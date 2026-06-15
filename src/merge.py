#!/usr/bin/env python3
"""
merge — ELF binary binder

Embeds two binaries as base64 payloads inside a self-contained Python stub
and writes it as an executable output file.  Running the output file
executes both originals in sequence.
"""

import base64
import os
import stat
import sys


STUB_TEMPLATE = """\
#!/usr/bin/env python3
import base64
import os
import stat
import subprocess
import tempfile

PAYLOAD1 = "{payload1}"
PAYLOAD2 = "{payload2}"


def run_payload(b64_data):
    data = base64.b64decode(b64_data)
    fd, tmp = tempfile.mkstemp()
    try:
        os.write(fd, data)
        os.close(fd)
        os.chmod(tmp, stat.S_IRWXU)
        subprocess.run([tmp], check=False)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


run_payload(PAYLOAD1)
run_payload(PAYLOAD2)
"""


def print_usage(prog: str) -> None:
    print("Welcome to the merge program.")
    print(f"Usage: {prog} source-binary1 source-binary2 -o output-binary")


def read_binary(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as exc:
        print(f"Error: cannot open '{path}': {exc.strerror}", file=sys.stderr)
        return None


def check_executable(path: str, data: bytes) -> None:
    elf_magic = b"\x7fELF"
    shebang   = b"#!"
    if data[:4] != elf_magic and data[:2] != shebang:
        print(
            f"Warning: '{path}' does not appear to be an executable (no ELF magic or shebang)",
            file=sys.stderr,
        )


def build_stub(data1: bytes, data2: bytes) -> str:
    return STUB_TEMPLATE.format(
        payload1=base64.b64encode(data1).decode(),
        payload2=base64.b64encode(data2).decode(),
    )


def write_executable(path: str, content: str) -> bool:
    try:
        with open(path, "w") as f:
            f.write(content)
        os.chmod(
            path,
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
        )
        return True
    except OSError as exc:
        print(f"Error: cannot write '{path}': {exc.strerror}", file=sys.stderr)
        return False


def main() -> int:
    prog = sys.argv[0]

    if len(sys.argv) == 1:
        print_usage(prog)
        return 1

    if len(sys.argv) != 5 or sys.argv[3] != "-o":
        print_usage(prog)
        return 1

    bin1_path, bin2_path, out_path = sys.argv[1], sys.argv[2], sys.argv[4]

    data1 = read_binary(bin1_path)
    if data1 is None:
        return 1

    data2 = read_binary(bin2_path)
    if data2 is None:
        return 1

    check_executable(bin1_path, data1)
    check_executable(bin2_path, data2)

    stub = build_stub(data1, data2)

    if not write_executable(out_path, stub):
        return 1

    print(f"{bin1_path} and {bin2_path} merged into {out_path} successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
