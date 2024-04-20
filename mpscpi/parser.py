#!/usr/bin/env python
# -*- coding: utf-8 -*-

from re import compile

IGNORECASE = const(2)


def to_regex(command: str) -> str:
    """
    Return a regular expression string from the given command expression.
    """

    regex, low_zone = r"\:?", False
    for c in command:
        if not c.islower():
            if low_zone:
                regex += ")?"
            low_zone = False
        if c == "[":
            regex += "("
        elif c == "]":
            regex += ")?"
        elif c.islower():
            if not low_zone:
                regex += "("
            low_zone = True
            regex += c.upper()
        elif c in "*:":
            regex += "\\" + c
        else:
            regex += c
    if low_zone:
        regex += ")?"
    return regex + "$"


def to_compiled_regex(command: str):
    """
    Return a compiled regular expression object from the given command expression.
    """

    regex = to_regex(command)
    return compile(regex, IGNORECASE)


def split_line(line: str, separator: str = ";") -> list:
    """
    Split line into multiple requests.
    """

    line = line.strip().strip(separator)
    requests = []
    for request_string in line.split(separator):
        if not request_string:
            continue
        query = "?" in request_string
        request_string = request_string.replace("?", "")
        name, _, args = request_string.partition(" ")
        name, args = name.strip(), args.strip()
        requests.append((name, args, query))
    return requests
