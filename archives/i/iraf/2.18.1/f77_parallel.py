#!/usr/bin/env python3
"""Bounded build-time scheduling of independent upstream f77.sh invocations."""
import concurrent.futures
import errno
import os
import subprocess
import sys
import time


RESOURCE_ERRORS = (errno.ENOMEM, errno.EAGAIN)


def invoke(command, capture=False):
    """Report whether a process failed to start, distinct from compiler failure."""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.STDOUT if capture else None)
        return result.returncode, result.stdout or b"", None
    except OSError as error:
        if error.errno in RESOURCE_ERRORS:
            return 1, b"", error
        if not capture:
            print(error, file=sys.stderr)
            return 1, b"", None
        return 1, (str(error) + "\n").encode(), None


def invoke_serial(command, capture=False):
    """Bound retries to process-start resource errors; never retry compiler exits."""
    for attempt, delay in enumerate((0, 2, 5, 10), 1):
        if delay:
            time.sleep(delay)
        code, output, resource = invoke(command, capture)
        if resource is None:
            return code, output, False
        print(f"IRAF scheduler: spawn errno={resource.errno}, attempt={attempt}, "
              f"input={command[-1]}", file=sys.stderr)
    return 1, output, True


def main():
    args = sys.argv[1:]
    real = os.environ["IRAF_F77_SERIAL"]
    workers = max(1, min(4, int(os.environ.get("IRAF_F77_WORKERS", "4"))))
    files = [arg for arg in args if not arg.startswith("-") and arg.endswith((".f", ".F"))]
    mixed = any(not arg.startswith("-") and arg.endswith((".c", ".s", ".o", ".e")) for arg in args)
    if "-c" not in args or "-o" in args or mixed or len(files) < 2:
        return invoke_serial([real, *args])[0]
    flags = [arg for arg in args if arg not in files]

    def compile_one(filename):
        return invoke([real, *flags, filename], capture=True)

    results = {}
    next_index = 0
    resource_pressure = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        running = {}
        while running or (next_index < len(files) and not resource_pressure):
            while not resource_pressure and len(running) < workers and next_index < len(files):
                running[pool.submit(compile_one, files[next_index])] = next_index
                next_index += 1
            completed, _ = concurrent.futures.wait(running,
                            return_when=concurrent.futures.FIRST_COMPLETED)
            for future in completed:
                index = running.pop(future)
                results[index] = future.result()
                if results[index][2] is not None:
                    print(f"IRAF scheduler: spawn errno={results[index][2].errno}, "
                          f"input={files[index]}", file=sys.stderr)
                    resource_pressure = True

    if resource_pressure:
        print("IRAF scheduler: process-start resource pressure; running workers drained, "
              "continuing unstarted inputs serially", file=sys.stderr)
        exhausted = False
        for index, filename in enumerate(files):
            if index in results and results[index][2] is None:
                continue
            if exhausted:
                results[index] = (1, b"Not started after resource retry limit\n", None)
                continue
            code, output, exhausted = invoke_serial([real, *flags, filename], capture=True)
            results[index] = (code, output, None)

    failed = False
    for index, filename in enumerate(files):
        code, output, _ = results[index]
        if output:
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
        if code:
            print("IRAF f77 failed: " + filename, file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
