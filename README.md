# mpscpi

Instrumentation framework for network-based
SCPI communication in MicroPython applications.

## Background

This is accomplished by providing a layer of
abstraction using a TCP socket, asynchronous
callback handler and SCPI command parser to
allow to ease instrumentation 

## Installation

### Repository

If not already done, install mpremote.

```shell
python3 -m venv venv
source venv/bin/activate
pip install mpremote
```

Use mpremote and mip to install from GitHub.

```shell
mpremote mip install github:mcpcpc/mpscpi
```

## Usage

### Quickstart

The following is a basic example of how to spin 
up a new server instance.

```micropython
from mpscpi import MPSCPI

app = MPSCPI(__name__)

if __name__ == "__main__":
    app.run("127.0.0.1", 5025)
```

Note that mpscpi leaves instantiation of the
network interface up to the user; thus, it is
recommended to call the `run()` command only
after connectivity is confirmed.

### Custom Callbacks

Custom user functions are implemented using the
built-in callback handlers.

```micropython
app.push("FOO", func=lambda a: None)
app.pull("FOO", func=lambda a: "BAR")
```

### Syntax Conventions

- Braces ({}) enclose the parameter choices for a
  given command string. The braces are not sent
  with the command string.
- Vertical bars (|) separar multiple paramater
  choices for a given command string.
- Triangle brackets (<>) indicate that you must
  specify a value for the enclosed parameter. The
  brackets are not sent with the command string.
  Square brackets ([]) indicate optional
  parameters that can be omitted. The brackets
  are not sent with the command string.

## To Do

- Complete IEEE 488.2 protocol compliance (will
  accept pull requests).
- Argument string parser class for numeric,
  boolean and array data types.

## Contact

For further questions or concerns, feel free to
contact me at michaelczigler[at]icloud[dot]com.
