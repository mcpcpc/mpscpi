"""
Network reliability tests for MPSCPI server.
Tests connection handling, error recovery, and sustained operation.
"""

import socket
import time
import statistics


HOST = "10.0.0.3"
PORT = 5025
TCP_NODELAY = True


def make_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if TCP_NODELAY:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.settimeout(10)
    sock.connect((HOST, PORT))
    return sock


def send_command(sock: socket.socket, cmd: str) -> str:
    sock.sendall((cmd + "\n").encode())
    if "?" in cmd:
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk
        return data.decode().strip()
    return ""


def test_reconnect(cycles: int = 20) -> dict:
    """Test repeated connect/disconnect cycles."""
    print(f"\n[TEST] Reconnect stability ({cycles} cycles)...")
    failures = 0
    latencies = []
    for i in range(cycles):
        try:
            start = time.perf_counter()
            sock = make_socket()
            resp = send_command(sock, "*IDN?")
            elapsed = (time.perf_counter() - start) * 1000
            sock.close()
            if "GEHC" not in resp:
                failures += 1
                print(f"  Cycle {i}: unexpected response: {resp!r}")
            else:
                latencies.append(elapsed)
        except Exception as e:
            failures += 1
            print(f"  Cycle {i}: {e}")
        time.sleep(0.1)
    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: {cycles - failures}/{cycles} successful")
    if latencies:
        print(f"  Connect+query avg: {statistics.mean(latencies):.1f} ms")
    return {"name": "reconnect", "passed": passed, "failures": failures}


def test_rapid_commands(count: int = 500) -> dict:
    """Test rapid-fire commands without pausing."""
    print(f"\n[TEST] Rapid-fire commands ({count} queries)...")
    sock = make_socket()
    failures = 0
    for i in range(count):
        try:
            state = "HIGH" if i % 2 == 0 else "LOW"
            send_command(sock, f":GPIO29 {state}")
            resp = send_command(sock, ":GPIO29?")
            expected = "HIGH" if i % 2 == 0 else "LOW"
            if resp != expected:
                failures += 1
                if failures <= 5:
                    print(f"  Cmd {i}: expected {expected!r}, got {resp!r}")
        except Exception as e:
            failures += 1
            if failures <= 5:
                print(f"  Cmd {i}: {e}")
    sock.close()
    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: {count - failures}/{count} correct responses")
    return {"name": "rapid_commands", "passed": passed, "failures": failures}


def test_partial_send() -> dict:
    """Test sending a command byte-by-byte (fragmented TCP)."""
    print("\n[TEST] Fragmented/partial send...")
    sock = make_socket()
    failures = 0
    commands = [":GPIO29 HIGH", ":GPIO29?", ":GPIO29 LOW", ":GPIO29?"]
    expected_responses = ["HIGH", "LOW"]

    resp_idx = 0
    for cmd in commands:
        # Send character by character with small delays
        for ch in cmd:
            sock.sendall(ch.encode())
            time.sleep(0.005)
        sock.sendall(b"\n")

        if "?" in cmd:
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(1024)
                if not chunk:
                    break
                data += chunk
            resp = data.decode().strip()
            if resp != expected_responses[resp_idx]:
                failures += 1
                print(f"  Expected {expected_responses[resp_idx]!r}, got {resp!r}")
            resp_idx += 1

    sock.close()
    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: fragmented messages handled correctly")
    return {"name": "partial_send", "passed": passed, "failures": failures}


def test_invalid_commands() -> dict:
    """Test server handles invalid/unknown commands gracefully."""
    print("\n[TEST] Invalid/unknown commands...")
    sock = make_socket()
    failures = 0

    # Send garbage, then a valid query to confirm server still works
    invalid_cmds = [
        "",
        "INVALID_COMMAND",
        ":NONEXISTENT HIGH",
        "!@#$%^&*()",
        ":GPIO999 HIGH",
        "A" * 200,
    ]
    for cmd in invalid_cmds:
        try:
            send_command(sock, cmd)
        except Exception as e:
            failures += 1
            print(f"  Server crashed on {cmd!r}: {e}")
            sock = make_socket()

    # Verify server still responds correctly after garbage
    try:
        resp = send_command(sock, "*IDN?")
        if "GEHC" not in resp:
            failures += 1
            print(f"  After garbage: unexpected IDN response: {resp!r}")
    except Exception as e:
        failures += 1
        print(f"  After garbage: {e}")

    sock.close()
    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: server survived invalid commands")
    return {"name": "invalid_commands", "passed": passed, "failures": failures}


def test_semicolon_batch() -> dict:
    """Test multiple semicolon-separated commands in one line."""
    print("\n[TEST] Semicolon-separated batch commands...")
    sock = make_socket()
    failures = 0

    # Set multiple GPIOs then query them
    send_command(sock, ":GPIO29 HIGH;:GPIO14 LOW;:GPIO28 HIGH")
    r1 = send_command(sock, ":GPIO29?")
    r2 = send_command(sock, ":GPIO14?")
    r3 = send_command(sock, ":GPIO28?")

    if r1 != "HIGH":
        failures += 1
        print(f"  GPIO29: expected HIGH, got {r1!r}")
    if r2 != "LOW":
        failures += 1
        print(f"  GPIO14: expected LOW, got {r2!r}")
    if r3 != "HIGH":
        failures += 1
        print(f"  GPIO28: expected HIGH, got {r3!r}")

    sock.close()
    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: batch commands processed correctly")
    return {"name": "semicolon_batch", "passed": passed, "failures": failures}


def test_sustained_connection(duration_s: int = 30) -> dict:
    """Test sustained operation over a single connection."""
    print(f"\n[TEST] Sustained connection ({duration_s}s)...")
    sock = make_socket()
    failures = 0
    count = 0
    start = time.time()

    while time.time() - start < duration_s:
        try:
            state = "HIGH" if count % 2 == 0 else "LOW"
            send_command(sock, f":GPIO29 {state}")
            resp = send_command(sock, ":GPIO29?")
            expected = "HIGH" if count % 2 == 0 else "LOW"
            if resp != expected:
                failures += 1
            count += 1
        except Exception as e:
            failures += 1
            print(f"  Failed at cmd {count}: {e}")
            break

    elapsed = time.time() - start
    sock.close()
    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: {count} commands in {elapsed:.1f}s, {failures} failures")
    print(f"  Throughput: {count / elapsed:.1f} cmd/s")
    return {"name": "sustained", "passed": passed, "failures": failures, "count": count}


def test_abrupt_disconnect() -> dict:
    """Test server recovery after client disconnects abruptly."""
    print("\n[TEST] Abrupt disconnect recovery...")
    failures = 0

    # Connect, send partial data, then kill socket
    for i in range(5):
        try:
            sock = make_socket()
            sock.sendall(b":GPIO29 HI")  # partial command, no newline
            sock.close()  # abrupt close
            time.sleep(0.2)
        except Exception:
            pass

    # Verify server is still accepting connections
    time.sleep(0.5)
    try:
        sock = make_socket()
        resp = send_command(sock, "*IDN?")
        if "GEHC" not in resp:
            failures += 1
            print(f"  After abrupt disconnects: unexpected response: {resp!r}")
        sock.close()
    except Exception as e:
        failures += 1
        print(f"  Server not responding after abrupt disconnects: {e}")

    passed = failures == 0
    print(f"  {'PASS' if passed else 'FAIL'}: server recovered from abrupt disconnects")
    return {"name": "abrupt_disconnect", "passed": passed, "failures": failures}


def main():
    print(f"Network Reliability Tests - {HOST}:{PORT}")
    print("=" * 50)

    results = []
    results.append(test_reconnect())
    results.append(test_rapid_commands())
    results.append(test_partial_send())
    results.append(test_invalid_commands())
    results.append(test_semicolon_batch())
    results.append(test_sustained_connection())
    results.append(test_abrupt_disconnect())

    # Summary
    print("\n" + "=" * 50)
    print("  SUMMARY")
    print("=" * 50)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}")
    print(f"\n  {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
