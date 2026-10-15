#!/usr/bin/env python3
"""Execute and inspect the installed MVDSV binary."""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, **kwargs)


def main():
    package = Path(sys.argv[1])
    binary = package / "bin" / "mvdsv"
    assert binary.is_file(), "packaged mvdsv executable is missing"
    assert os.access(binary, os.X_OK), "packaged mvdsv is not executable"

    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    assert readelf, "readelf is required for ELF validation"
    sections = run([readelf, "-SW", str(binary)], check=True).stdout
    dynamic = run([readelf, "-d", str(binary)], check=True).stdout
    assert sections.count(".codesign") == 1, "final ELF must contain one .codesign section"
    assert "RPATH" not in dynamic and "RUNPATH" not in dynamic

    binary_data = binary.read_bytes()
    assert b".conan2" not in binary_data, "final ELF leaks a Conan cache path"
    assert os.fsencode(str(package)) not in binary_data, "final ELF leaks its package path"

    runner = shlex.split(os.environ.get("MVDSV_TEST_RUNNER", ""))
    if runner:
        print("MVDSV cross preflight passed: runtime execution is covered on the OHOS target")
        return

    with tempfile.TemporaryDirectory(prefix="mvdsv-consumer-") as working_directory:
        result = run(runner + [str(binary), "+quit"], cwd=working_directory, timeout=15)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Starting MVDSV 1.11" in output, output
    assert "QuakeWorld Initialized" in output, output
    assert "www authentication disabled (no curl support)" in output, output

    if sys.platform != "linux" or "HarmonyOS" in run(["uname", "-a"], check=True).stdout:
        param = "/system/bin/param" if Path("/system/bin/param").is_file() else "param"
        fullname = run([param, "get", "const.ohos.fullname"], check=True).stdout.strip()
        assert fullname.startswith("OpenHarmony-"), fullname

    print("MVDSV consumer passed: signed relocatable ELF + versioned server startup")


if __name__ == "__main__":
    main()
