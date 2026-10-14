#!/usr/bin/env python3
import os
import pathlib
import shutil
import subprocess
import sys


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run_case(client, module, password_file, password):
    environment = os.environ.copy()
    environment["CVM_PWFILE_PATH"] = str(password_file)
    return subprocess.run(
        [client, module, "testuser", "", password],
        check=False,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_commands.py PACKAGE_BIN WORK_DIR")

    package_bin = pathlib.Path(sys.argv[1])
    work_dir = pathlib.Path(sys.argv[2])
    packaged_commands = sorted(package_bin.glob("cvm-*"))
    check(len(packaged_commands) == 13, "expected 13 packaged CVM commands")
    patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
    check(pathlib.Path(patchelf).is_file(), "patchelf is required for RUNPATH audit")
    runpaths = {
        command.name: subprocess.run(
            [patchelf, "--print-rpath", str(command)],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        for command in packaged_commands
    }
    leaking = {name: value for name, value in runpaths.items() if value}
    check(not leaking, "RPATH/RUNPATH in packaged commands: " + repr(leaking))
    client = str(package_bin / "cvm-testclient")
    module = str(package_bin / "cvm-pwfile")
    check(pathlib.Path(client).is_file(), "packaged cvm-testclient is missing")
    check(pathlib.Path(module).is_file(), "packaged cvm-pwfile is missing")

    password_file = work_dir / "cvm-test-passwords"
    password_file.write_text(
        "testuser:testpass:123:456:Test User:/data:/bin/false\n",
        encoding="utf-8",
    )

    accepted = run_case(client, module, password_file, "testpass")
    check(accepted.returncode == 0, accepted.stdout)
    for expected in (
        "user name:        testuser",
        "user ID:          123",
        "group ID:         456",
        "directory:        /data",
    ):
        check(expected in accepted.stdout, "missing output: " + expected)

    rejected = run_case(client, module, password_file, "wrong")
    check(rejected.returncode == 100, rejected.stdout)
    check("Credentials rejected" in rejected.stdout, rejected.stdout)
    print("packaged command transport accepted and rejected credentials correctly")


if __name__ == "__main__":
    main()
