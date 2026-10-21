"""Real task-local PTY adapter for the upstream script -qfc tests only.

No test results, isatty values or terminal bytes are fabricated. Unsupported
command shapes fail closed. The child receives a real controlling terminal.
"""
import errno
import os
import pty
import select
import signal
import sys
import time

if len(sys.argv) != 4 or sys.argv[1] != '-qfc' or sys.argv[3] != '/dev/null':
    raise SystemExit('supported invocation: -qfc COMMAND /dev/null')
shell = os.environ.get('CONFIG_SHELL')
if not shell or not os.path.isabs(shell):
    raise SystemExit('CONFIG_SHELL must bind the real build-context shell')
pid, master = pty.fork()
if pid == 0:
    os.execv(shell, [shell, '-c', sys.argv[2]])
deadline = time.monotonic() + 180
try:
    while True:
        if time.monotonic() >= deadline:
            # pty.fork creates this child's own session/process group.
            if os.getpgid(pid) != pid:
                raise RuntimeError('owned PTY process identity changed')
            os.killpg(pid, signal.SIGKILL)
            raise TimeoutError('PTY command exceeded 180 seconds')
        ready, _, _ = select.select([master], [], [], 1)
        if not ready:
            continue
        try:
            block = os.read(master, 65536)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not block:
            break
        sys.stdout.buffer.write(block)
        sys.stdout.buffer.flush()
finally:
    os.close(master)
    _, status = os.waitpid(pid, 0)
raise SystemExit(os.waitstatus_to_exitcode(status))
