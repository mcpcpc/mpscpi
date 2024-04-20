#!/usr/bin/env python
# -*- coding: utf-8 -*-

from asyncio import get_event_loop
from asyncio import start_server

from .parser import split_line
from .parser import to_compiled_regex


class MPSCPI:
    """
    Server with asynchronous callback.
    """

    commands: dict = {}

    def __init__(self, import_name: str) -> None:
        self.import_name = import_name

    def push(self, name: str, func) -> None:
        """
        Method for registering `push` commands.
        """

        if not self.commands.get(name, None):
            regex = to_compiled_regex(name)
            self.commands[name] = dict(re=regex)
        self.commands[name]["push"] = func

    def pull(self, name: str, func) -> None:
        """
        Method for registering `pull` commands.
        """

        if not self.commands.get(name, None):
            regex = to_compiled_regex(name)
            self.commands[name] = dict(re=regex)
        self.commands[name]["pull"] = func

    def find(self, value: str) -> dict:
        """
        Find the first matching command for a given string.
        """

        for command in commands.values():
            regex = command.get("re")
            if regex.match(value):
                return command
        return None

    async def callback(self, reader, writer) -> None:
        """
        Called when some data is received. data is a non-empty
        bytes object containing the incoming data.
        """

        peername = reader.get_extra_info("peername")
        print(f"Peer connected on: {peername}")
        while True:
            message = yield from reader.readline()
            if message == b"":
                print(f"Resetting peer: {peername}")
                break  # close connection
            message_utf = message.decode()
            for name, args, query in split_line(message_utf):
                command = self.find(name)
                if not command:
                    continue  # not found
                if not query:
                    push = command.get("push")
                    push(args)
                    continue
                pull = command.get("pull")
                response = pull(args)
                writer.write(response.encode())
                await writer.drain()
        writer.close()
        await writer.wait_closed()

    def run(self, host: str, port: int) -> None:
        """
        Run asynchronous service.
        """

        loop = get_event_loop()
        coro = start_server(self.callback, host, port)
        try:
            print(f"Serving on: {host}")
            loop.create_task(coro)
            loop.run_forever()
        except KeyboardInterrupt:
            print("keyboard interrupt")
            loop.close()
        print("server closed")
