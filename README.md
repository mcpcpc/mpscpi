# mpscpi

Instrumentation framework for network-based
SCPI communication in MicroPython applications.

## Installation

### Repository

If not done already install mpremote.

```shell
python3 -m venv venv
source venv/bin/activate
pip install mpremote
```

Use mpremote and mip to install the source files.

```shell
mpremote mip install github:mcpcpc/mpscpi
```

## Usage

### Quickstart

The following is a basic example of how to spin 
up a new server instance. Note that mpscpi
leaves instantiation of the network interface up
to the user.

```micropython
from mpscpi import MPSCPI

app = MPSCPI(__name__)

if __name__ == "__main__":
    app.run("127.0.0.1", 5025)
```

### Custom Callbacks

Custom user functions are implemented using the
built-in callback handlers.

```micropython
app.push("FOO", lambda a: None)
app.pull("FOO", lambda a: "BAR")  # returns "BAR"
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

## Contact

For further questions or concerns, feel free to
contact me at michaelczigler[at]icloud[dot]com.
