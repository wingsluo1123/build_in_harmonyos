#!/bin/sh
# Offline run-time verification for the installed xaric 0.13.9 binary.
#
# xaric is a full-screen terminal IRC client.  main() hard-requires a TTY on
# stdin (irc.c:798 `if (!isatty(0)) { ... exit(1); }`) and only then parses
# argv and prints the version (irc.c:194 `case 'v': puts(PACKAGE_STRING)`).
# A plain redirection cannot exercise it, so this script drives the binary
# through a PTY via python3 (always available wherever Conan executes).
#
# OHOS-specific value: the binary statically links libncursesw.a for tgetent
# (OHOS ships no libtermcap/libcurses; see patches/0001-tgetent-ncursesw.patch)
# plus static libssl/libcrypto.  Starting the binary inside a PTY and reading
# its version output proves the whole static link set resolves and executes
# on the device, and that the XARIC_DATA_PATH help files were installed.
set -u

BIN_DIR="${1:-}"
DATA_DIR="${2:-}"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[ -n "$BIN_DIR" ] || fail "usage: test_xaric.sh <package>/bin <package>/share/xaric"
[ -d "$BIN_DIR" ] || fail "bin directory not found: $BIN_DIR"
[ -x "$BIN_DIR/xaric" ] || fail "xaric binary missing or not executable"
[ -f "$DATA_DIR/help/help" ] || fail "help data not installed at $DATA_DIR/help/help"

# Working dir for capture output: prefer a confirmed-writable location.
work_dir="${TMPDIR:-.}/xaric-test-$$"
mkdir -p "$work_dir" || fail "cannot create working directory $work_dir"

# Run `xaric -v` under a PTY and capture stdout+stderr to a file.
python3 - "$BIN_DIR/xaric" "$work_dir/version.out" <<'PYEOF'
import os
import pty
import sys
import time

exe = sys.argv[1]
out_path = sys.argv[2]

pid, fd = pty.fork()
if pid == 0:
    os.execv(exe, [exe, "-v"])

chunks = []
deadline = time.time() + 30
while time.time() < deadline:
    try:
        data = os.read(fd, 4096)
    except OSError:
        break
    if not data:
        break
    chunks.append(data)

os.close(fd)
try:
    os.waitpid(pid, 0)
except OSError:
    pass

with open(out_path, "wb") as handle:
    handle.write(b"".join(chunks))
PYEOF

captured=$(cat "$work_dir/version.out")
echo "$captured"

echo "$captured" | grep -q "Xaric 0.13.9" \
    || fail "xaric -v did not report 'Xaric 0.13.9' (got: $captured)"

rm -rf "$work_dir"

echo "PASS: installed xaric starts under PTY and reports version 0.13.9"
