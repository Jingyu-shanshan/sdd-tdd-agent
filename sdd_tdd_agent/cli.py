import sys
from typing import Optional, Sequence, TextIO


def hello(out: TextIO) -> None:
    """Write the platform greeting to the supplied output stream."""
    out.write("Hello, World!\n")


def main(
    argv: Optional[Sequence[str]] = None,
    out: Optional[TextIO] = None,
) -> int:
    """Run the command-line interface."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    output = sys.stdout if out is None else out

    if arguments and arguments[0] == "hello":
        hello(output)
        return 0

    return 2
