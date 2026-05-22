# -*- coding: utf-8 -*-

from micropython import const
from re import compile

IGNORECASE = const(2)


def to_regex(command: str) -> str:
    """
    Return a regular expression string from the given command expression.

    Supported syntax conventions:
      - {A|B}  → parameter choices (escaped as literal regex)
      - [OPT]  → optional group
      - <>     → required parameters (passed through literally)
      - MixedCase → each uppercase letter starts a new optional group
                    for flexible colon-stripping (e.g. "VOLT" matches
                    ":VOLT", "VOLT", ":VOL:TAG", etc.)
    """

    if not command:
        return r"^$"

    regex, low_zone = r"\:?", False
    for c in command:
        if not c.islower():
            if low_zone:
                regex += ")?"
            low_zone = False
        if c == "[":
            regex += "(?:"
        elif c == "]":
            regex += ")?"
        elif c == "{" or c == "}":
            # Escape brace literals — these are documentation placeholders
            regex += "\\" + c
        elif c.islower():
            if not low_zone:
                regex += "(?:"
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
    Split a line into individual SCPI requests.

    Handles whitespace around the separator so that
    "CMD1 ; CMD2" correctly yields two commands.
    """

    line = line.strip().strip(separator)
    requests = []
    for request_string in line.split(separator):
        request_string = request_string.strip()
        if not request_string:
            continue
        query = "?" in request_string
        request_string = request_string.replace("?", "").strip()
        name, _, args = request_string.partition(" ")
        name, args = name.strip(), args.strip()
        requests.append((name, args, query))
    return requests
