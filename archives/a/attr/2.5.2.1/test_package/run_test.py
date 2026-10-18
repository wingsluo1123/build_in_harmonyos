#!/usr/bin/env python3
"""Run the libattr consumer and installed command-line tools without hiding FS errors."""
import errno
import os
import re
import shutil
import subprocess
import sys
import tempfile


def report(label, command, cwd):
    executable = shutil.which(command[0])
    if executable is None:
        print("{} FAIL cause=not-found PATH={!r}".format(
            label, os.environ.get("PATH", "")))
        return "FAIL"
    argv = [executable] + list(command[1:])
    try:
        result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, errors="replace")
    except OSError as exc:
        print("{} FAIL raw_errno={} raw_error={!r}".format(
            label, getattr(exc, "errno", None), str(exc)))
        return "FAIL"
    status = "PASS" if result.returncode == 0 else "FAIL"
    print("{} {} executable={} exit_code={}".format(
        label, status, executable, result.returncode))
    if result.stdout:
        print("{} STDOUT {!r}".format(label, result.stdout))
    if result.stderr:
        print("{} STDERR {!r}".format(label, result.stderr))
    return status


def main():
    if len(sys.argv) != 3:
        print("CONSUMER FAIL cause=expected-one-test-binary")
        print("CONSUMER-SUMMARY total=6 pass=0 fail=1 notrun=5")
        return 2

    tool_bin = os.path.abspath(sys.argv[2])
    os.environ["PATH"] = tool_bin + os.pathsep + os.environ.get("PATH", "")
    print("PACKAGE-TOOL-BIN={}".format(tool_bin))

    cwd = os.getcwd()
    fd, path = tempfile.mkstemp(prefix="attr-conan-xattr-", dir=cwd)
    os.close(fd)
    outcomes = {}
    xattr_errno = None
    try:
        try:
            result = subprocess.run([sys.argv[1], path], cwd=cwd,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, errors="replace")
            print("LIBATTR-CONSUMER exit_code={}".format(result.returncode))
            if result.stdout:
                print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
            if result.stderr:
                print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
            combined = result.stdout + result.stderr
            for operation in ("attr_set", "attr_get"):
                match = re.search(
                    r"LIBATTR " + operation + r" (PASS|FAIL|NOTRUN)", combined)
                if match:
                    outcomes[operation] = match.group(1)
                else:
                    outcomes[operation] = "NOTRUN"
            if result.returncode != 0 and all(
                    outcomes[operation] == "NOTRUN" for operation in ("attr_set", "attr_get")):
                outcomes["attr_set"] = "FAIL"
                print("LIBATTR attr_set FAIL cause=consumer-exit-without-result")
                print("LIBATTR attr_get NOTRUN cause=consumer-exit-without-result")
            for line in combined.splitlines():
                if " errno=" in line:
                    try:
                        xattr_errno = int(line.split(" errno=", 1)[1].split()[0])
                    except ValueError:
                        pass
            if xattr_errno is not None:
                print("FILESYSTEM-XATTR-BOUNDARY raw_errno={} errno_name={} message={!r}".format(
                    xattr_errno, errno.errorcode.get(xattr_errno, "UNKNOWN"),
                    os.strerror(xattr_errno)))
        except OSError as exc:
            print("LIBATTR-CONSUMER FAIL raw_errno={} raw_error={!r}".format(
                getattr(exc, "errno", None), str(exc)))
            outcomes["attr_set"] = "NOTRUN"
            outcomes["attr_get"] = "NOTRUN"

        cli = (
            ("setfattr", ["setfattr", "-n", "user.attr_tool_probe",
                           "-v", "setfattr-probe", path]),
            ("getfattr", ["getfattr", "--only-values", "-n",
                           "user.attr_tool_probe", path]),
            ("attr_set_tool", ["attr", "-s", "user.attr_legacy_probe",
                               "-V", "attr-probe", path]),
            ("attr_get_tool", ["attr", "-g", "user.attr_legacy_probe", path]),
        )
        for label, command in cli:
            outcomes[label] = report(label.upper(), command, cwd)

        passed = sum(value == "PASS" for value in outcomes.values())
        failed = sum(value == "FAIL" for value in outcomes.values())
        notrun = sum(value == "NOTRUN" for value in outcomes.values())
        print("CONSUMER-SUMMARY total=6 pass={} fail={} notrun={}".format(
            passed, failed, notrun))
        return 0 if failed == 0 and notrun == 0 else 1
    finally:
        try:
            os.unlink(path)
        except OSError as exc:
            print("TEMP-FILE-CLEANUP FAIL raw_errno={} raw_error={!r}".format(
                getattr(exc, "errno", None), str(exc)))


if __name__ == "__main__":
    sys.exit(main())
