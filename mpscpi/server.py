# -*- coding: utf-8 -*-

import asyncio

from .parser import split_line
from .parser import to_compiled_regex


class MPSCPI:
    """
    Server with asynchronous callback.
    """

    def __init__(self, import_name: str) -> None:
        self.import_name = import_name
        self.commands = {}  # { command_name: { "re": compiled_re, "push": fn, "pull": fn } }
        self._prefix_map = {}  # { full_key: [command_names] }
        self._server = None
        self._tasks = []

    def push(self, name: str, func) -> None:
        """
        Method for registering `push` commands.
        """

        if not self.commands.get(name, None):
            regex = to_compiled_regex(name)
            self.commands[name] = dict(re=regex)
            self._add_prefix(name)
        self.commands[name]["push"] = func

    def pull(self, name: str, func) -> None:
        """
        Method for registering `pull` commands.
        """

        if not self.commands.get(name, None):
            regex = to_compiled_regex(name)
            self.commands[name] = dict(re=regex)
            self._add_prefix(name)
        self.commands[name]["pull"] = func

    def _add_prefix(self, name: str) -> None:
        """
        Register a command name in the prefix lookup map.

        Uses the full second colon-delimited segment as the key
        (e.g. "VOLT:RANG" -> key "RANG") for fine-grained candidate
        resolution and minimal collision risk.
        """
        parts = name.split(":")
        if len(parts) >= 2:
            key = parts[1]
        else:
            key = name[:3]
        self._prefix_map.setdefault(key, []).append(name)

    def find(self, value: str) -> dict:
        """
        Find the first matching command for a given string.

        Uses a prefix-map for efficient candidate resolution,
        then validates with regex matching.
        """
        parts = value.split(":")
        if len(parts) >= 2:
            key = parts[1]
        else:
            key = value[:3]
        candidates = self._prefix_map.get(key, [])
        for name in candidates:
            command = self.commands.get(name)
            if command and command.get("re").match(value):
                return command
        return None

    async def callback(self, reader, writer) -> None:
        """
        Called when a client connects. Handles incoming SCPI commands
        with graceful error recovery.
        """

        peername = reader.get_extra_info("peername")
        print(f"Peer connected on: {peername}")
        try:
            writer.get_extra_info("socket").setsockopt(6, 1, 1)
        except Exception:
            pass
        try:
            while True:
                message = await reader.readline()
                if message == b"":
                    print(f"Resetting peer: {peername}")
                    break  # close connection
                message_utf = message.decode()
                buf = bytearray()
                try:
                    for name, args, query in split_line(message_utf):
                        command = self.find(name)
                        if not command:
                            continue  # not found
                        if not query:
                            push = command.get("push")
                            if push:
                                push(args)
                            continue
                        pull = command.get("pull")
                        if pull:
                            response = pull(args)
                            if response is not None:
                                buf.extend(str(response).encode())
                except Exception as e:
                    # Log callback errors but don't kill the connection
                    print(f"Command error on {peername}: {e}")
                if buf:
                    writer.write(buf)
                    await writer.drain()
        except OSError as e:
            print(f"Connection error on {peername}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except OSError:
                pass  # already closed

    def run(self, host: str, port: int) -> None:
        """
        Run the asynchronous SCPI server.
        """

        loop = asyncio.get_event_loop()
        try:
            coro = asyncio.start_server(self.callback, host, port)
            self._server = loop.run_until_complete(coro)
            print(f"Serving on: {host}:{port}")
            loop.run_forever()
        except KeyboardInterrupt:
            print("keyboard interrupt")
        finally:
            self.stop()
            loop.close()
            print("server closed")

    def stop(self) -> None:
        """
        Gracefully shut down the server.
        """
        if self._server:
            self._server.close()
            self._server.wait_closed()
            print("Server stopped")
