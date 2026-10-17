#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys
import tempfile
import time


checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def run(command, environment, timeout=5, cwd=None):
    return subprocess.run(
        command,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
    )


def helper_is_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main():
    executable = pathlib.Path(sys.argv[1]).resolve()
    source = pathlib.Path(sys.argv[2]).resolve()
    helper_dir = source / "fake-bin"
    temporary = tempfile.TemporaryDirectory(prefix="qsoas-consumer-")
    work = pathlib.Path(temporary.name)

    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PATH"] = str(helper_dir) + os.pathsep + environment.get("PATH", "")
    function_file = source / "function.py"

    version = run([str(executable), "--version"], environment, cwd=work)
    check(version.returncode == 0, f"--version failed: {version.stderr}")
    check("QSoas version 3.3" in version.stdout, version.stdout)
    check("Built reproducibly from QSoas 3.3 release source" in version.stdout,
          version.stdout)

    valid_environment = environment.copy()
    valid_environment["QSOAS_TEST_HELPER_MODE"] = "valid"
    valid_environment["QSOAS_EXTERNAL_FUNCTION_TIMEOUT_MS"] = "2000"
    valid = run(
        [str(executable), "--pyfunc", str(function_file), "sample", "2", "4"],
        valid_environment,
        cwd=work,
    )
    check(valid.returncode == 0, f"valid helper failed: {valid.stderr}")
    check("Function: sample -> 8" in valid.stdout, valid.stdout)

    pid_file = work / "helper.pid"
    deadline_environment = environment.copy()
    deadline_environment["QSOAS_TEST_HELPER_MODE"] = "drip"
    deadline_environment["QSOAS_TEST_HELPER_PID_FILE"] = str(pid_file)
    deadline_environment["QSOAS_EXTERNAL_FUNCTION_TIMEOUT_MS"] = "500"
    started = time.monotonic()
    deadline = run(
        [str(executable), "--pyfunc", str(function_file), "sample", "1", "3"],
        deadline_environment,
        timeout=3,
        cwd=work,
    )
    elapsed = time.monotonic() - started
    check(deadline.returncode != 0, "unterminated response was accepted")
    check(elapsed < 2.5, f"transaction deadline was refreshed: {elapsed:.3f}s")
    check("transaction deadline" in deadline.stderr, deadline.stderr)
    helper_pid = int(pid_file.read_text(encoding="utf-8").strip())
    check(not helper_is_alive(helper_pid),
          f"timed-out helper {helper_pid} was not reaped")

    flood_pid_file = work / "flood-helper.pid"
    flood_environment = environment.copy()
    flood_environment["QSOAS_TEST_HELPER_MODE"] = "flood"
    flood_environment["QSOAS_TEST_HELPER_PID_FILE"] = str(flood_pid_file)
    flood_environment["QSOAS_EXTERNAL_FUNCTION_TIMEOUT_MS"] = "500"
    started = time.monotonic()
    flooded = run(
        [str(executable), "--pyfunc", str(function_file), "sample", "1", "3"],
        flood_environment,
        timeout=3,
        cwd=work,
    )
    flood_elapsed = time.monotonic() - started
    check(flooded.returncode != 0, "continuous complete lines bypassed the deadline")
    check(flood_elapsed < 2.5,
          f"continuous readable data bypassed the deadline: {flood_elapsed:.3f}s")
    check("transaction deadline" in flooded.stderr, flooded.stderr)
    flood_pid = int(flood_pid_file.read_text(encoding="utf-8").strip())
    check(not helper_is_alive(flood_pid),
          f"flooding helper {flood_pid} was not reaped")

    exit_environment = environment.copy()
    exit_environment["QSOAS_TEST_HELPER_MODE"] = "exit"
    exit_environment["QSOAS_EXTERNAL_FUNCTION_TIMEOUT_MS"] = "1000"
    exited = run(
        [str(executable), "--pyfunc", str(function_file), "sample", "1", "3"],
        exit_environment,
        cwd=work,
    )
    check(exited.returncode != 0, "premature helper exit was accepted")
    check("ended before completing" in exited.stderr, exited.stderr)

    print(f"qsoas consumer checks: {checks}/{checks} passed")


if __name__ == "__main__":
    main()
