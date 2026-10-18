#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the ReZound graphical audio editor.
#
# ReZound produces no library, so the consumer view is: install the package and
# use the program.  This script locates the installed binary, verifies it is an
# OpenHarmony aarch64 ELF, verifies the packaged data files, and then actually
# executes it.  The build/test machine has no X server, so ReZound must fail
# while opening the display — and only there: reaching FOX's
# "unable to open display" message proves that every shared library it was
# linked against (libFOX-1.6 -> libX11/libXext, ...) was resolved by the
# loader, which is exactly what breaks for a mis-packaged GUI dependency chain.
set -uo pipefail

fail() { echo "❌ $*"; exit 1; }
ok() { echo "✅ $*"; }

SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
LOG="$SCRATCH/rezound-consumer-test-$$.log"
cleanup() { rm -f "$LOG"; }
trap cleanup EXIT

# ── 1. the installed programme is reachable ────────────────────────────────
REZOUND="$(command -v rezound || true)"
[ -n "$REZOUND" ] || fail "rezound is not on PATH (VirtualRunEnv did not expose the package bin/)"
[ -x "$REZOUND" ] || fail "rezound is not executable: $REZOUND"
PREFIX="$(cd "$(dirname "$REZOUND")/.." && pwd)"
ok "installed binary: $REZOUND"
ok "installation prefix: $PREFIX"

# ── 2. it must be an OpenHarmony aarch64 ELF ───────────────────────────────
python3 - "$REZOUND" <<'PYEOF' || exit 1
import struct
import sys

path = sys.argv[1]
with open(path, "rb") as handle:
    header = handle.read(20)
if header[:4] != b"\x7fELF":
    sys.exit(f"❌ not an ELF file: {path}")
if header[4] != 2:
    sys.exit("❌ not a 64-bit ELF")
machine = struct.unpack_from("<H", header, 18)[0]
if machine != 0xB7:
    sys.exit(f"❌ ELF machine {machine:#x}, expected 0xB7 (AArch64)")
print("✅ ELF header OK: 64-bit AArch64")
PYEOF

# ── 3. the packaged data files are in place ────────────────────────────────
for data in presets.dat key_bindings.dat menu.dat impulse_hall1.wav icon_logo_32.gif; do
    [ -s "$PREFIX/share/rezound/$data" ] || fail "missing packaged data file: share/rezound/$data"
done
ok "packaged data files present: share/rezound/ (5 files)"

# ── 4. run the programme ───────────────────────────────────────────────────
unset DISPLAY
"$REZOUND" >"$LOG" 2>&1
rc=$?
output="$(cat "$LOG")"

case "$output" in
*"Error loading shared library"* | *"cannot open shared object file"*)
    fail "dynamic linker could not resolve the dependency chain:
$output"
    ;;
esac

case "$output" in
*"unable to open display"*) ;;
*)
    fail "rezound did not reach FOX display initialisation (rc=$rc):
$output"
    ;;
esac

[ "$rc" -ne 0 ] || fail "rezound unexpectedly succeeded without an X display"
ok "executed and initialised FOX; display probe failed as expected (rc=$rc)"

echo "🎉 rezound consumer test passed"
