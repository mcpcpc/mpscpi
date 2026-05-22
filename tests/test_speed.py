"""
Speed test for MPSCPI GPIO commands over TCP.
Sends push (set) and pull (query) commands and measures latency/throughput.
"""

import socket
import time
import statistics


HOST = "10.0.0.3"
PORT = 5025
NUM_ITERATIONS = 100


def send_command(sock: socket.socket, cmd: str) -> str:
    """Send a command and optionally read response (if query)."""
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


def benchmark_push(sock: socket.socket, iterations: int) -> list:
    """Benchmark push (set) commands."""
    latencies = []
    for i in range(iterations):
        state = "HIGH" if i % 2 == 0 else "LOW"
        start = time.perf_counter()
        send_command(sock, f":GPIO29 {state}")
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies


def benchmark_pull(sock: socket.socket, iterations: int) -> list:
    """Benchmark pull (query) commands."""
    latencies = []
    for i in range(iterations):
        start = time.perf_counter()
        resp = send_command(sock, ":GPIO29?")
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies


def benchmark_mixed(sock: socket.socket, iterations: int) -> list:
    """Benchmark alternating push then pull."""
    latencies = []
    for i in range(iterations):
        state = "HIGH" if i % 2 == 0 else "LOW"
        start = time.perf_counter()
        send_command(sock, f":GPIO29 {state}")
        resp = send_command(sock, ":GPIO29?")
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies

def benchmark_batch(sock: socket.socket, iterations: int) -> list:
    """Benchmark push+pull sent in a single TCP write (both lines at once)."""
    latencies = []
    for i in range(iterations):
        state = "HIGH" if i % 2 == 0 else "LOW"
        start = time.perf_counter()
        # Send both commands in one TCP segment
        sock.sendall(f":GPIO29 {state}\n:GPIO29?\n".encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies

def benchmark_multi_command(sock: socket.socket, iterations: int) -> list:
    """Benchmark sending multiple commands in one line (semicolon-separated)."""
    latencies = []
    for i in range(iterations):
        state = "HIGH" if i % 2 == 0 else "LOW"
        # Send 5 GPIO commands in a single line
        cmd = ";".join([f":GPIO{n} {state}" for n in [29, 14, 28, 15, 27]])
        start = time.perf_counter()
        send_command(sock, cmd)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies


def benchmark_combined(sock: socket.socket, iterations: int) -> list:
    """Benchmark push+pull in single line (semicolon-separated)."""
    latencies = []
    for i in range(iterations):
        state = "HIGH" if i % 2 == 0 else "LOW"
        # Send set + query as one command line - avoids Nagle/delayed-ACK
        cmd = f":GPIO29 {state};:GPIO29?"
        start = time.perf_counter()
        resp = send_command(sock, cmd)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies


def print_stats(name: str, latencies: list) -> None:
    """Print statistics for a set of latency measurements."""
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    print(f"  Iterations:  {len(latencies)}")
    print(f"  Mean:        {statistics.mean(latencies):.3f} ms")
    print(f"  Median:      {statistics.median(latencies):.3f} ms")
    print(f"  Std Dev:     {statistics.stdev(latencies):.3f} ms")
    print(f"  Min:         {min(latencies):.3f} ms")
    print(f"  Max:         {max(latencies):.3f} ms")
    print(f"  Throughput:  {1000 / statistics.mean(latencies):.1f} cmd/s")


def main():
    print(f"Connecting to {HOST}:{PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.settimeout(10)
    sock.connect((HOST, PORT))
    print("Connected.\n")

    # Warm up
    print("Warming up (10 commands)...")
    for i in range(10):
        send_command(sock, ":GPIO29 HIGH")
        send_command(sock, ":GPIO29?")

    print(f"\nRunning benchmarks ({NUM_ITERATIONS} iterations each)...")

    # Push benchmark
    push_latencies = benchmark_push(sock, NUM_ITERATIONS)
    print_stats("PUSH (set GPIO)", push_latencies)

    # Pull benchmark
    pull_latencies = benchmark_pull(sock, NUM_ITERATIONS)
    print_stats("PULL (query GPIO)", pull_latencies)

    # Mixed benchmark (separate sends)
    mixed_latencies = benchmark_mixed(sock, NUM_ITERATIONS)
    print_stats("MIXED (set + query, separate sends)", mixed_latencies)

    # Batch benchmark (single TCP write)
    batch_latencies = benchmark_batch(sock, NUM_ITERATIONS)
    print_stats("BATCH (set + query, single send)", batch_latencies)

    # Multi-command benchmark
    multi_latencies = benchmark_multi_command(sock, NUM_ITERATIONS)
    print_stats("MULTI (5 push cmds in one line)", multi_latencies)

    # Combined push+pull benchmark
    combined_latencies = benchmark_combined(sock, NUM_ITERATIONS)
    print_stats("COMBINED (push+pull in one line)", combined_latencies)

    # Overall summary
    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"{'='*50}")
    print(f"  Push avg:     {statistics.mean(push_latencies):.3f} ms")
    print(f"  Pull avg:     {statistics.mean(pull_latencies):.3f} ms")
    print(f"  Mixed avg:    {statistics.mean(mixed_latencies):.3f} ms")
    print(f"  Batch avg:    {statistics.mean(batch_latencies):.3f} ms")
    print(f"  Multi avg:    {statistics.mean(multi_latencies):.3f} ms")
    print(f"  Combined avg: {statistics.mean(combined_latencies):.3f} ms")

    sock.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
