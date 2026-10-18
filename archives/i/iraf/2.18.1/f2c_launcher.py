#!/usr/bin/env python3
"""Build-only recovery for an observed intermittent F2C exec EPERM."""
import errno
import os
import subprocess
import sys
import time


def launch(command, popen=None, sleeper=None):
    popen = popen or subprocess.Popen
    sleeper = sleeper or time.sleep
    for attempt, delay in enumerate((0, 1, 3), 1):
        if delay:
            sleeper(delay)
        try:
            child = popen(command, close_fds=False)
        except OSError as error:
            if error.errno != errno.EPERM or attempt == 3:
                print(f"IRAF F2C launcher: exec failed errno={error.errno}: {error}",
                      file=sys.stderr, flush=True)
                return 127 if error.errno in (errno.ENOENT, errno.ENOTDIR) else 126
            print(f"IRAF F2C launcher: exec errno={error.errno}, "
                  f"attempt={attempt}/3; retrying before compiler start",
                  file=sys.stderr, flush=True)
            continue
        # Keep wait outside the OSError handler: an already started compiler
        # is never retried, including nonzero exits and signal termination.
        code = child.wait()
        return code if code >= 0 else 128 - code
    return 126


def main():
    real = os.environ.get("IRAF_F2C_REAL", "")
    if not os.path.isabs(real) or os.path.realpath(real) == os.path.realpath(__file__):
        print("IRAF_F2C_REAL must identify the absolute real F2C executable",
              file=sys.stderr)
        return 126
    return launch([real, *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
