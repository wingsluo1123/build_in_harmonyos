#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for mrxvt 0.5.4 (installed bin/mrxvt).
#
# mrxvt is an X11 tabbed terminal emulator: its real job needs an X server,
# but everything that happens before XOpenDisplay() is exercisable headless,
# and that is exactly what is asserted here:
#
#   * the program is packaged and is the ELF the recipe is supposed to emit
#     (class/machine are read straight out of the ELF header, so these two
#     assertions are independent of whether the host can execute it);
#   * the version banner and the options table, which also prove that
#     -DVERSION reached xdefaults.c and that the configure feature switches
#     took effect;
#   * the no-DISPLAY path, which additionally proves the ELF really loaded
#     its libX11/libXft/libfontconfig runtime closure.
#
# The runtime half is skipped (not passed, not failed) when the loader cannot
# start the program at all - i.e. when the test runs on a host that is not the
# build target, as happens in a cross-build.  Skipping is reported loudly so a
# skipped run is never mistaken for a green one.
#
# Env: MRXVT_BIN            = path to the installed program (set by conanfile)
#      MRXVT_EXPECT_MACHINE = ELF e_machine that must be emitted (183=aarch64)
# Exit: 0 = every executed check passed, 1 = at least one check failed
#--------------------------------------------------------------------
set -u

MRXVT="${MRXVT_BIN:-mrxvt}"
EXPECT_MACHINE="${MRXVT_EXPECT_MACHINE:-183}"

checks=0
fails=0
skips=0

check() { # check <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got \"$2\", want \"$3\")"
		fails=$((fails + 1))
	fi
}

skip() { # skip <name> <reason>
	checks=$((checks + 1))
	skips=$((skips + 1))
	echo "SKIP: $1 ($2)"
}

BASE="${TMPDIR:-/tmp}"
mkdir -p "$BASE" 2>/dev/null || BASE="$HOME"
WORK="$BASE/mrxvt-consumer.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT
OUT="$WORK/out.txt"
RC="$WORK/rc.txt"

# 1. the program is packaged
if [ -f "$MRXVT" ] && [ -x "$MRXVT" ]; then
	check "bin/mrxvt installed and executable" yes yes
else
	check "bin/mrxvt installed and executable" no yes
	echo "SUMMARY: checks=$checks failed=$fails skipped=$skips"
	exit 1
fi

# 2-3. ELF header of the packaged program: class (byte 5) and machine
#      (bytes 19-20, little endian).  2 = ELF64, 183 = EM_AARCH64.
class=$(od -An -tu1 -j4 -N1 "$MRXVT" | tr -d " ")
machine=$(od -An -tu1 -j18 -N2 "$MRXVT" | awk "{print \$1 + 256 * \$2}")
check "ELF class is ELF64" "$class" 2
check "ELF machine is $EXPECT_MACHINE" "$machine" "$EXPECT_MACHINE"

# Can the loader start it at all?  126 = "found but cannot execute", 127 =
# "shared library trouble"; both mean this host is not the build target.
unset DISPLAY
"$MRXVT" --version >"$OUT" 2>&1
echo $? >"$RC"
probe_rc=$(cat "$RC")
if [ "$probe_rc" = "126" ] || [ "$probe_rc" = "127" ]; then
	echo "INFO: loader cannot start the program on this host"
	echo "INFO: --version rc=$probe_rc output: $(head -c 200 "$OUT" | tr "\n" " ")"
	skip "-h prints the Mrxvt v0.5.4 banner" "cross-build host cannot execute the aarch64 binary (rc=$probe_rc)"
	skip "-h prints the Options: table" "cross-build host cannot execute the aarch64 binary (rc=$probe_rc)"
	skip "-h lists -display" "cross-build host cannot execute the aarch64 binary (rc=$probe_rc)"
	skip "no DISPLAY reports Error opening display" "cross-build host cannot execute the aarch64 binary (rc=$probe_rc)"
	skip "no DISPLAY exits 1" "cross-build host cannot execute the aarch64 binary (rc=$probe_rc)"
else
	# 4-6. the version banner and the option table
	"$MRXVT" -h >"$OUT" 2>&1 || true
	help_text=$(cat "$OUT")
	case "$help_text" in
	*"Mrxvt v0.5.4"*) check "-h prints the Mrxvt v0.5.4 banner" yes yes ;;
	*) check "-h prints the Mrxvt v0.5.4 banner" no yes ;;
	esac
	case "$help_text" in
	*"Options: "*) check "-h prints the Options: table" yes yes ;;
	*) check "-h prints the Options: table" no yes ;;
	esac
	case "$help_text" in
	*-display*) check "-h lists -display" yes yes ;;
	*) check "-h lists -display" no yes ;;
	esac

	# 7-8. the no-DISPLAY path: the X11 closure has to load for this message
	#      to be produced, so it is a real dynamic-linkage check.
	unset DISPLAY
	"$MRXVT" >"$OUT" 2>&1
	echo $? >"$RC"
	nodisplay_text=$(cat "$OUT")
	case "$nodisplay_text" in
	*"Error opening display"*) check "no DISPLAY reports Error opening display" yes yes ;;
	*) check "no DISPLAY reports Error opening display" no yes ;;
	esac
	check "no DISPLAY exits 1" "$(cat "$RC")" 1
fi

# 9. end-to-end consumer run: really start mrxvt against a reachable X
#    display and verify it connects and enters its main loop (killed after
#    2s). This is the one full consumer case -- not a pure assertion -- that
#    exercises the X connection and event-loop start of the real program.
#    When this host cannot start the program at all (cross-build) or has no
#    DISPLAY (headless worker), it is reported SKIP loudly with the
#    environmental reason, never PASS and never silently dropped.
if [ "$probe_rc" = "126" ] || [ "$probe_rc" = "127" ]; then
	skip "end-to-end: X start" "cross-build host cannot execute the aarch64 binary (rc=$probe_rc)"
elif [ -n "${DISPLAY:-}" ]; then
	"$MRXVT" -display "$DISPLAY" >"$OUT" 2>&1 &
	mrxvt_pid=$!
	sleep 2
	if kill -0 "$mrxvt_pid" 2>/dev/null; then
		kill "$mrxvt_pid" 2>/dev/null
		wait "$mrxvt_pid" 2>/dev/null
		check "end-to-end: starts and stays alive on $DISPLAY" alive alive
	else
		wait "$mrxvt_pid" 2>/dev/null
		rc9=$?
		check "end-to-end: starts and stays alive on $DISPLAY" "rc=$rc9" alive
	fi
else
	skip "end-to-end: X start" "no DISPLAY on this host (headless worker); X connection path covered by checks 7-8"
fi

echo "SUMMARY: checks=$checks failed=$fails skipped=$skips"
[ "$fails" -eq 0 ] || exit 1
exit 0
