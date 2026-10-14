#!/usr/bin/env python3
import os
import pathlib
import shutil
import subprocess
import sys


PROGRAMS = (
    "cvm-benchclient", "cvm-chain", "cvm-checkpassword", "cvm-pwfile",
    "cvm-qmail", "cvm-testclient", "cvm-unix", "cvm-v1benchclient",
    "cvm-v1checkpassword", "cvm-v1testclient", "cvm-vmailmgr",
    "cvm-vmailmgr-local", "cvm-vmailmgr-udp",
)
LIBRARIES = (
    "cvm-v2client", "cvm-v1client", "cvm-module", "cvm-command",
    "cvm-local", "cvm-udp", "cvm-sql", "cvm-sasl", "cvm-qmail",
)
LEAK_MARKERS = (b"/.conan2/", b"/storage/Users/", b"/home/")
assertions = 0


def check(condition, message):
    global assertions
    assertions += 1
    if not condition:
        raise AssertionError(message)


def output(command):
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def needed_is_closed(path, patchelf, search_dirs):
    missing = []
    for needed in output([patchelf, "--print-needed", str(path)]).splitlines():
        if needed and not any((directory / needed).exists() for directory in search_dirs):
            missing.append(needed)
    return missing


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_elf.py PACKAGE_ROOT")

    package = pathlib.Path(sys.argv[1])
    bin_dir = package / "bin"
    lib_dir = package / "lib"
    patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
    readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
    check(pathlib.Path(patchelf).is_file(), "patchelf is required")
    check(pathlib.Path(readelf).is_file(), "llvm-readelf is required")

    search_dirs = [lib_dir]
    search_dirs.extend(
        pathlib.Path(entry)
        for entry in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
        if entry
    )
    search_dirs.extend(pathlib.Path(path) for path in (
        "/system/lib64", "/system/lib", "/usr/lib", "/lib",
    ))

    commands = [bin_dir / name for name in PROGRAMS]
    check(len(commands) == 13, "expected 13 command audit targets")
    for command in commands:
        check(command.is_file(), "missing command: " + str(command))
        check(not output([patchelf, "--print-rpath", str(command)]),
              "command RPATH/RUNPATH is not empty: " + str(command))
        data = command.read_bytes()
        check(not any(marker in data for marker in LEAK_MARKERS),
              "command contains a private build path: " + str(command))
        sections = output([readelf, "--sections", "--wide", str(command)])
        check(sections.count(".codesign") == 1,
              "command must contain exactly one .codesign: " + str(command))
        missing = needed_is_closed(command, patchelf, search_dirs)
        check(not missing, f"unresolved NEEDED for {command}: {missing}")

    for name in LIBRARIES:
        stem = "lib" + name + ".so"
        real_files = [
            path for path in lib_dir.glob(stem + ".*")
            if path.is_file() and not path.is_symlink()
        ]
        check(len(real_files) == 1, f"expected one real file for {stem}: {real_files}")
        real = real_files[0]
        soname = output([patchelf, "--print-soname", str(real)])
        check(soname.startswith(stem + "."), f"invalid SONAME for {real}: {soname}")
        linker_link = lib_dir / stem
        soname_link = lib_dir / soname
        check(linker_link.is_symlink() and linker_link.resolve() == real.resolve(),
              "broken linker-name symlink: " + str(linker_link))
        check(soname_link.is_symlink() and soname_link.resolve() == real.resolve(),
              "broken SONAME symlink: " + str(soname_link))
        check(not output([patchelf, "--print-rpath", str(real)]),
              "library RPATH/RUNPATH is not empty: " + str(real))
        data = real.read_bytes()
        check(not any(marker in data for marker in LEAK_MARKERS),
              "library contains a private build path: " + str(real))
        missing = needed_is_closed(real, patchelf, search_dirs)
        check(not missing, f"unresolved NEEDED for {real}: {missing}")

    print(f"ELF closure, SONAME, path and signature audit passed: {assertions} assertions")


if __name__ == "__main__":
    main()
