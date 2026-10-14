#!/usr/bin/env bash
# test_package/test.sh — drives the packaged levee the way a user does:
# scripted keystrokes on stdin, the terminal database of Conan ncurses/6.6
# through TERMINFO, and a private writable $TMPDIR.
#
#   1-8  functional checks and negative controls
#   9    HarmonyOS consumer flow: levee edits consumer.c.in, the profile's OHOS
#        compiler builds the edited source, the program runs and verifies it
#
# usage: test.sh <levee> <terminfo-dir> <c-compiler> <test_package-dir> <work-dir>
set -euo pipefail

LEVEE="${1:?packaged levee binary}"
TERMINFO_DIR="${2:?terminfo directory}"
CC_BIN="${3:?C compiler}"
TP_DIR="${4:?test_package directory}"
WORK="${5:?work directory}"
TOTAL=9

passed=0
ok()   { passed=$((passed + 1)); echo "[ok]   $*"; }
fail() { echo "[fail] $*" >&2; exit 1; }

[ -x "$LEVEE" ] || fail "packaged levee binary not found: $LEVEE"
[ -f "$TERMINFO_DIR/v/vt100" ] || fail "vt100 entry missing in $TERMINFO_DIR"

# AArch64 hosts (the HarmonyOS CI device) run the static PIEs directly; other
# hosts need qemu-aarch64.  A missing emulator is a failure, never a skip.
runner=()
case "$(uname -m)" in
    aarch64|arm64) ;;
    *)
        qemu="$(command -v qemu-aarch64)" || fail "qemu-aarch64 is required on $(uname -m)"
        runner=("$qemu")
        ;;
esac

rm -rf "$WORK"
mkdir -p "$WORK/tmp"
cd "$WORK"

# ncurses ignores TERMINFO, TERMINFO_DIRS and $HOME/.terminfo for uid 0 (only
# its compiled-in //share/terminfo is searched), so a root runner executes
# levee as an unprivileged uid inside a user namespace.  That uid can only read
# files owned by the mapped root uid, hence a root-owned copy of the one entry
# the checks use.  Conan runs as a normal user on the HarmonyOS device and
# never takes this branch.
as_user=()
if [ "$(id -u)" = "0" ]; then
    unshare --user --map-user=65534 --map-group=65534 true 2>/dev/null ||
        fail "running as root without user namespaces: ncurses would ignore TERMINFO"
    as_user=(unshare --user --map-user=65534 --map-group=65534)
    mkdir -p "$WORK/terminfo/v"
    cp "$TERMINFO_DIR/v/vt100" "$WORK/terminfo/v/vt100"
    TERMINFO_DIR="$WORK/terminfo"
fi

EXTRA_ENV=()
# lev <tmpdir> <keys> [levee args...]: type <keys> (printf %b escapes) into
# levee; the screen output goes to screen.out.  Every script ends with a quit
# command; the timeout only guards against a script that does not.
lev() {
    local tmpdir="$1" keys="$2" rc=0
    shift 2
    printf '%b' "$keys" | timeout 60 \
        ${as_user[@]+"${as_user[@]}"} env TERM=vt100 \
        TERMINFO="$TERMINFO_DIR" TERMINFO_DIRS="$TERMINFO_DIR" TMPDIR="$tmpdir" \
        ${EXTRA_ENV[@]+"${EXTRA_ENV[@]}"} \
        ${runner[@]+"${runner[@]}"} "$LEVEE" "$@" > screen.out 2>&1 || rc=$?
    return "$rc"
}

screen_has() {
    local screen
    screen="$(cat screen.out)"
    case "$screen" in *"$1"*) return 0 ;; esac
    return 1
}

make_rows() {
    local i=1
    while [ "$i" -le 128 ]; do
        printf '    ROW(%3d),  /* levee yank block, line %03d */\n' "$i" "$i"
        i=$((i + 1))
    done
}

# 1-2. --version / --help (patch 0002), answered without touching the terminal
out="$(${runner[@]+"${runner[@]}"} "$LEVEE" --version < /dev/null)" || fail "--version exited $?"
[ "$out" = "levee 4.0" ] || fail "--version printed '$out'"
ok "--version prints 'levee 4.0' and exits 0"
out="$(${runner[@]+"${runner[@]}"} "$LEVEE" --help < /dev/null)" || fail "--help exited $?"
case "$out" in "usage: levee "*) ;; *) fail "--help printed '$out'" ;; esac
ok "--help prints the usage line and exits 0"

# 3. visual mode: insert two lines into a new file, write and quit
lev "$WORK/tmp" 'ifirst line\rsecond line\x1b:wq\r' new.txt || fail "insert/:wq exited $?"
printf 'first line\nsecond line\n' > new.expect
cmp -s new.expect new.txt || fail "new file content differs from the typed text"
ok "insert mode + :wq writes exactly the typed lines"

# 4. -r: the buffer can change but :w is refused and the file stays intact
printf 'keep me\n' > ro.txt
cp ro.txt ro.expect
lev "$WORK/tmp" 'ichanged \x1b:w\r:q!\r' -r ro.txt || fail "-r session exited $?"
cmp -s ro.expect ro.txt || fail "-r: the file was modified"
screen_has "File is readonly" || fail "-r: no 'File is readonly' message"
ok "-r refuses :w with 'File is readonly', file unchanged"

# 5. terminal layer: levee's termcap calls go to the statically linked
#    libncursesw, which must load vt100 from TERMINFO; stdin is not a tty, so
#    the screen height comes from tgetnum("li") and ncurses applies LINES
printf 'alpha\n' > t.txt
EXTRA_ENV=(LINES=30 COLUMNS=100)
lev "$WORK/tmp" ':q\r' t.txt || fail "terminal session exited $?"
EXTRA_ENV=()
screen_has $'\033[30;1H' || fail "no vt100 cursor addressing to row 30 on the screen"
ok "vt100 'cm' from the ncurses terminfo database, height 30 from LINES"

# 6. dd deletes the current line, u restores it
printf 'one\ntwo\nthree\n' > u1.txt
cp u1.txt u2.txt
lev "$WORK/tmp" '2Gdd:wq\r' u1.txt || fail "dd session exited $?"
printf 'one\nthree\n' > u1.expect
cmp -s u1.expect u1.txt || fail "2Gdd did not delete line 2"
lev "$WORK/tmp" '2Gddu:wq\r' u2.txt || fail "undo session exited $?"
printf 'one\ntwo\nthree\n' > u2.expect
cmp -s u2.expect u2.txt || fail "u did not restore the deleted line"
ok "dd deletes line 2, u restores it"

make_rows > rows.inc
cp "$TP_DIR/consumer.c.in" template.c

# Keystrokes shared by the consumer edit (9) and the negative controls (7, 8).
# ":s" reports "N substitution" and leaves a "[more]" prompt in visual mode;
# the extra \r dismisses it (":r" leaves none, there \r would move a line).
# The rows part reads the 128 lines in front of the marker (the cursor stays
# on the first one), yanks them (6 KiB) and puts them after line 128.
KEYS_STAMP=':1,$s/@STAMP@/edited by levee 4.0/\r\r'
KEYS_FRUIT='/@FRUIT@\rj4!!sort\r'
KEYS_ROWS='/@ROWS@\r:r rows.inc\r128yy/@ROWS@\rkp'

# 7. negative control for patch 0003, yank spill: the same keystrokes as the
#    consumer edit, but $TMPDIR points to a missing directory, so the 6 KiB
#    yank cannot spill to disk and the put adds nothing.  /tmp is writable on
#    this host, so this proves the spill file goes under $TMPDIR (the
#    HarmonyOS device has a read-only /tmp)
cp template.c neg-yank.c
lev "$WORK/missing" "${KEYS_ROWS}:wq\\r" neg-yank.c || fail "negative yank session exited $?"
# grep -c exits 1 when it counts no row at all; the count is checked right below
rows="$(grep -c '^    ROW(' neg-yank.c)" || true
[ "$rows" = "128" ] || fail "negative yank: expected the 128 read rows only, found $rows"
ok "6 KiB yank/put adds nothing when \$TMPDIR is missing (rows stay 128)"

# 8. negative control for patch 0003, ! filter: the scratch file cannot be
#    created under a missing $TMPDIR -> "[tempfile error]", nothing written
cp template.c neg-filter.c
lev "$WORK/missing" "${KEYS_FRUIT}"'\x1b:q!\r' neg-filter.c ||
    fail "negative filter session exited $?"
screen_has "[tempfile error]" || fail "negative filter: no '[tempfile error]' message"
cmp -s template.c neg-filter.c || fail "negative filter: the file was modified"
ok "! filter reports [tempfile error] when \$TMPDIR is missing"

# 9. HarmonyOS consumer flow: levee edits the consumer source (ex substitute,
#    ! filter through /bin/sh, :r + 6 KiB yank/put, both temp files under
#    $TMPDIR), the OHOS compiler builds it, the program checks every edit
cp template.c consumer.c
lev "$WORK/tmp" "${KEYS_STAMP}${KEYS_FRUIT}${KEYS_ROWS}:wq\\r" consumer.c ||
    fail "consumer edit session exited $?"
[ -z "$(ls -A "$WORK/tmp")" ] || fail "levee left temporary files in \$TMPDIR"
"$CC_BIN" -O2 -fPIE -static-pie -o consumer consumer.c || fail "consumer build failed"
out="$(${runner[@]+"${runner[@]}"} ./consumer)" || fail "consumer exited $?: $out"
echo "       $out"
case "$out" in "consumer ok:"*"rows=256 sum=16512") ;; *) fail "unexpected consumer output" ;; esac
ok "levee-edited consumer.c built by $CC_BIN and run: all edits verified"

[ "$passed" -eq "$TOTAL" ] || fail "only $passed/$TOTAL checks ran"
echo "levee test_package: $passed/$TOTAL checks passed"
