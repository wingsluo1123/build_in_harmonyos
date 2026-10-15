#!/usr/bin/env python3
"""Consumer probe for the packaged Asterisk ODBC modules."""

import os
import pathlib
import re
import shutil
import subprocess
import sys


MODULES = [
    "res_odbc_transaction.so",
    "res_odbc.so",
    "res_config_odbc.so",
    "func_odbc.so",
    "cdr_odbc.so",
    "cdr_adaptive_odbc.so",
    "cel_odbc.so",
]

SAMPLES = [
    "res_odbc.conf.sample",
    "res_config_odbc.conf.sample",
    "func_odbc.conf.sample",
    "cdr_odbc.conf.sample",
    "cdr_adaptive_odbc.conf.sample",
    "cel_odbc.conf.sample",
]

TOOL_TIMEOUT_SECONDS = 15


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def run_tool(args):
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"command timed out after {TOOL_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"cannot execute {' '.join(args)}: {exc}") from exc


def find_tool(*names):
    fallback_dirs = [
        pathlib.Path(path)
        for path in (
            os.environ.get("OHOS_TOOL_BIN"),
            pathlib.Path(sys.executable).parent,
            pathlib.Path.home() / "usr" / "local" / "bin",
            "/data/service/hnp/bin",
        )
        if path
    ]
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
        for tool_dir in fallback_dirs:
            tool = tool_dir / name
            if tool.is_file():
                return str(tool)
    return None


def check_module(path):
    if not path.is_file():
        return fail(f"missing module: {path}")
    if path.stat().st_size <= 0:
        return fail(f"empty module: {path}")
    try:
        magic = path.read_bytes()[:4]
    except OSError as exc:
        return fail(f"cannot read {path}: {exc}")
    if magic != b"\x7fELF":
        return fail(f"{path} is not ELF (magic={magic!r})")

    elf_header_tool = find_tool("llvm-readelf", "readelf", "llvm-readobj")
    if not elf_header_tool:
        return fail(
            "llvm-readelf, readelf, or llvm-readobj is required to validate packaged modules"
        )
    tool_name = pathlib.Path(elf_header_tool).name
    args = [elf_header_tool, "--file-headers", str(path)] if tool_name == "llvm-readobj" else [
        elf_header_tool, "-h", str(path)
    ]
    try:
        result = run_tool(args)
    except RuntimeError as exc:
        return fail(str(exc))
    if result.returncode != 0 or "elf" not in result.stdout.lower():
        return fail(f"ELF header inspection failed for {path}: {result.stderr[:400]}")
    type_pattern = r"Type:\s+SharedObject" if tool_name == "llvm-readobj" else r"Type:\s+DYN"
    if not re.search(type_pattern, result.stdout):
        return fail(f"{path} is not an ELF shared object")

    nm = find_tool("llvm-nm", "nm")
    if not nm:
        return fail("llvm-nm or nm is required to validate Asterisk module symbols")
    try:
        result = run_tool([nm, str(path)])
    except RuntimeError as exc:
        return fail(str(exc))
    if result.returncode != 0:
        return fail(f"nm failed for {path}: {result.stderr[:400]}")
    if "ast_module_info" not in result.stdout and "load_module" not in result.stdout:
        return fail(f"{path} has no Asterisk module symbol")

    print(f"PASS: {path.name} is a non-empty Asterisk ELF module")
    return 0


def main():
    if len(sys.argv) != 2:
        return fail("usage: test_asterisk_odbc.py <package_folder>")

    pkg = pathlib.Path(sys.argv[1])
    module_dir = pkg / "lib" / "asterisk" / "modules"
    res_dir = pkg / "res"

    for module in MODULES:
        rc = check_module(module_dir / module)
        if rc:
            return rc

    for sample in SAMPLES:
        path = res_dir / sample
        if not path.is_file() or path.stat().st_size <= 0:
            return fail(f"missing or empty sample config: {path}")
        print(f"PASS: sample config present: {sample}")

    print("PASS: asterisk-odbc package verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
