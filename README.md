# merge — ELF Binary Binder

## Table of Contents

1. [Explanation of the Binder](#explanation-of-the-binder)
2. [Walkthrough](#walkthrough)
3. [Binary File Structure](#binary-file-structure)
4. [Usage Instructions](#usage-instructions)
5. [Ethical and Legal Report](#ethical-and-legal-report)

---

## Explanation of the Binder

`merge` is a **binary binder**: a tool that takes two independently compiled
Linux ELF executables and produces a single new executable that, when run,
executes both originals in sequence.

### How it works — high-level

```
  bin1 ──┐
         ├─► merge ──► bin3  (runs bin1, then bin2)
  bin2 ──┘
```

`merge` uses a **base64 stub embedding** strategy:

1. Read `bin1` and `bin2` entirely into memory.
2. Base64-encode both payloads.
3. Inject them into a Python stub template that, at runtime, decodes each
   payload, writes it to a temp file, makes it executable, and runs it via
   `subprocess.run`, then cleans up.
4. Write the populated stub to the output path and mark it executable
   (`chmod 755`).

The output file is a self-contained Python script with a shebang line —
no compiler, no external dependencies, no temp files at bind-time.

### Why this approach

| Approach | Pros | Cons |
|---|---|---|
| Base64 stub (this project) | No compiler needed at bind-time; clean Python; readable output | Output is a script, requires Python 3 at run-time |
| C hex-array + gcc | Native ELF output | Requires gcc at bind-time; large generated source |
| Append after stub | Compact output | Needs a pre-compiled stub template baked into `merge` |

The base64 stub approach was chosen for its simplicity, readability, and
because Python 3 is universally available on modern Linux systems.

---

## Walkthrough

### Step 1 — Parse arguments

`main()` in `src/merge.py` validates the argument count and the `-o` flag.
With no arguments it prints the usage banner and exits with code 1.

```
Usage: ./merge source-binary1 source-binary2 -o output-binary
```

### Step 2 — Validate inputs

`check_elf()` reads the first 4 bytes of each input and compares them to
the ELF magic `\x7fELF`.  A warning is printed for non-ELF files, but
binding continues — the binder treats all inputs as opaque byte blobs.

### Step 3 — Read both binaries

`read_binary()` opens each path in binary mode (`"rb"`) and returns the
full contents as a `bytes` object.

### Step 4 — Build the stub

`build_stub()` base64-encodes both payloads and formats them into
`STUB_TEMPLATE`:

```python
PAYLOAD1 = "f0VMRgIBAQAAAAAAAAAAAAIAPgABAAAA..."
PAYLOAD2 = "f0VMRgIBAQAAAAAAAAAAAAIAPgABAAAA..."

def run_payload(b64_data):
    data = base64.b64decode(b64_data)
    fd, tmp = tempfile.mkstemp()
    try:
        os.write(fd, data)
        os.close(fd)
        os.chmod(tmp, stat.S_IRWXU)
        subprocess.run([tmp], check=False)
    finally:
        os.unlink(tmp)

run_payload(PAYLOAD1)
run_payload(PAYLOAD2)
```

The temp files exist only for the duration of each child process and are
always removed in the `finally` block.

### Step 5 — Write the output

`write_executable()` writes the populated stub string to the output path,
then sets permissions to `755` (owner rwx, group/others rx) so it can be
run directly.

### Step 6 — Report

The binder prints a success message and exits with code 0.

---

## Binary File Structure

### ELF (Executable and Linkable Format)

Linux executables follow the ELF specification.  Every ELF file starts with
a fixed-size header:

```
Offset  Size  Field
------  ----  ------------------------------------------
0x00    4     Magic number: 0x7f 'E' 'L' 'F'
0x04    1     EI_CLASS: 1 = 32-bit, 2 = 64-bit
0x05    1     EI_DATA: 1 = little-endian, 2 = big-endian
0x06    1     EI_VERSION: must be 1
0x07    1     EI_OSABI: 0 = System V / Linux
0x08    8     EI_ABIVERSION + padding
0x10    2     e_type: 2 = ET_EXEC (executable)
0x12    2     e_machine: 0x3e = x86-64
0x14    4     e_version
0x18    8     e_entry — virtual address of the entry point
0x20    8     e_phoff — offset to the program header table
0x28    8     e_shoff — offset to the section header table
...
```

Following the ELF header are:

- **Program headers** — describe memory segments (LOAD, DYNAMIC, INTERP …).
  The kernel uses these to map the binary into memory.
- **Sections** — `.text` (code), `.data` (initialised data), `.rodata`
  (read-only data), `.bss` (zero-initialised data), `.symtab`, `.strtab`, …
- **Section header table** — used by linkers and debuggers.

### What the binder does NOT modify

`merge` treats both input binaries as opaque byte blobs.  It does not parse,
patch, or relink their ELF headers, entry points, or sections.  Each binary
is preserved bit-for-bit in the base64 payload and extracted to a temp file
at runtime, so the OS loads and runs it exactly as if it had been invoked
directly.

### Inspecting a binary

```sh
readelf -h  bin/bin1        # ELF header
readelf -S  bin/bin1        # section headers
objdump -d  bin/bin1        # disassemble .text
xxd         bin/bin1 | head # raw hex dump
```

---

## Usage Instructions

### Prerequisites

- Linux (x86-64 recommended)
- Python 3.9+
- `make` (optional, for the provided Makefile)

### Building

```sh
make all          # installs bin/merge, compiles bin/bin1 and bin/bin2
```

Or manually:

```sh
cp src/merge.py bin/merge && chmod +x bin/merge
cp tests/bin1.py bin/bin1 && chmod +x bin/bin1
cp tests/bin2.py bin/bin2 && chmod +x bin/bin2
```

### Running the binder

```sh
# No arguments — print usage
./bin/merge

# Merge two binaries
./bin/merge bin/bin1 bin/bin2 -o bin/bin3
```

### Example session

```sh
$ ./bin/bin1
Message from bin1

$ ./bin/bin2
Message from bin2

$ ./bin/merge
Welcome to the merge program.
Usage: ./bin/merge source-binary1 source-binary2 -o output-binary

$ ./bin/merge bin/bin1 bin/bin2 -o bin/bin3
bin/bin1 and bin/bin2 merged into bin/bin3 successfully!

$ ./bin/bin3
Message from bin1
Message from bin2
```

### Running all tests

```sh
make test
```

### Cleaning build artefacts

```sh
make clean
```

---

## Ethical and Legal Report

### Legitimate uses of binary binding

Binary binding and analysis have well-established, lawful applications:

- **Software installers** — single-file installers that bundle multiple
  components (e.g., NSIS, makeself).
- **Forensic and malware analysis** — security researchers analyse how binders
  work in order to detect and reverse them.
- **Embedded systems** — combining firmware components into a single flashable
  image.
- **Penetration testing** — authorised red-team exercises use binder concepts
  to assess endpoint defences, always with written permission.
- **Education** — understanding executable formats, entry points, and OS
  loaders is foundational knowledge for any systems programmer.

### Misuse and legal risks

The same technique can be abused:

| Misuse | Legal / ethical problem |
|---|---|
| Binding malware to a legitimate application | Constitutes distribution of malicious software; criminal in most jurisdictions (e.g., Computer Fraud and Abuse Act (US), Computer Misuse Act (UK)) |
| Binding software without the owner's consent | Violates software licences; may infringe copyright |
| Bypassing antivirus or security products without authorisation | Prohibited under security-product terms of service and potentially under law |
| Using on systems you do not own or have no written authorisation to test | Unauthorised access is a criminal offence in virtually every jurisdiction |

### Responsible use guidelines

1. **Obtain written authorisation** before running any binary modification or
   analysis tool on a system or against software you do not own.
2. **Work in isolated environments** (VMs, containers) to prevent accidental
   impact on production systems.
3. **Disclose responsibly** — if you discover a vulnerability using these
   techniques, follow coordinated disclosure best practices.
4. **Respect licences** — many software licences explicitly prohibit
   reverse-engineering or modification.

### Defending against binary tampering

- **Code signing** — sign executables with a trusted key; the OS (or a policy
  engine) rejects unsigned or modified binaries.
- **Integrity checking** — store and verify SHA-256 hashes of deployed
  binaries.
- **Secure boot** — hardware-rooted trust chain validates every binary from
  firmware to userland.
- **Mandatory access control** — SELinux / AppArmor policies restrict which
  executables may be loaded and where.
- **EDR / AV** — endpoint detection tools flag unusual patterns such as
  writing an executable to `/tmp` and immediately running it.

> **Disclaimer:** This project is for educational purposes only. Use these
> techniques only on systems you own or have explicit written permission to
> test. Misuse may be illegal and unethical.
