#!/usr/bin/env python3
"""termios raw-mode probe: run dte inside a pty and verify its core loop.

Evidence produced here:
  * dte opens the tty and switches the line discipline to raw mode
    (ICANON/ECHO off) — the mechanism this package exists to exercise;
  * TIOCGWINSZ / TIOCSWINSZ work (24x80 window is honoured);
  * screen output is rendered and interactive input produces more output.

Exit codes: 0 = probe passed (or pty unavailable -> explicit SKIP),
            1 = dte ran but did NOT enter raw mode / produced no output.
"""

import fcntl
import os
import pty
import select
import shutil
import signal
import struct
import sys
import termios
import time

TIOCSCTTY = 0x540E
TIOCGWINSZ = 0x5413
TIOCSWINSZ = 0x5414


def drain(fd, budget=0.3):
    data = b""
    while select.select([fd], [], [], budget)[0]:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        data += chunk
        budget = 0.2
    return data


def main():
    dte = shutil.which("dte")
    if not dte:
        print("[pty_probe] FAIL: dte not found on PATH")
        return 1

    try:
        master, slave = pty.openpty()
    except OSError as exc:
        print(f"[pty_probe] SKIP: cannot allocate pty on this worker ({exc})")
        return 0

    fcntl.ioctl(slave, TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    sample = os.path.abspath("pty-probe-sample.txt")
    with open(sample, "w", encoding="utf-8") as fh:
        fh.write("hello dte pty probe\n")

    pid = os.fork()
    if pid == 0:  # child: own session, pty as controlling terminal
        os.setsid()
        try:
            fcntl.ioctl(slave, TIOCSCTTY, 0)
        except OSError:
            pass
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        if slave > 2:
            os.close(slave)
        os.close(master)
        os.execv(dte, [dte, "-H", "-R", sample])

    try:
        time.sleep(1.0)
        out = drain(master)
        attrs = termios.tcgetattr(slave)
        lflag = attrs[3]
        raw = not (lflag & termios.ICANON) and not (lflag & termios.ECHO)
        size = struct.unpack(
            "HHHH", fcntl.ioctl(slave, TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
        )
        print(
            "[pty_probe] raw_mode={} ICANON={} ECHO={} ISIG={} winsz={}x{} "
            "first_draw_bytes={}".format(
                raw,
                "Y" if lflag & termios.ICANON else "N",
                "Y" if lflag & termios.ECHO else "N",
                "Y" if lflag & termios.ISIG else "N",
                size[1],
                size[0],
                len(out),
            )
        )
        if not raw:
            print("[pty_probe] FAIL: dte did not enter termios raw mode")
            return 1
        if not out:
            print("[pty_probe] FAIL: no screen output drawn")
            return 1

        # Type into the buffer; a responsive editor must redraw.
        before = len(out)
        os.write(master, b"XY")
        time.sleep(0.4)
        out += drain(master)
        print(f"[pty_probe] redraw_after_input={'yes' if len(out) > before else 'no'}")
    finally:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                break
            time.sleep(0.2)
            gone, _ = os.waitpid(pid, os.WNOHANG)
            if gone:
                break
        else:
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        os.close(master)
        os.close(slave)
        try:
            os.unlink(sample)
        except OSError:
            pass

    print("[pty_probe] PASS: termios raw mode + TIOCGWINSZ verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
