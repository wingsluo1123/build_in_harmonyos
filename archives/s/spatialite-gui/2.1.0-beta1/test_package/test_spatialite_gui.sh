#!/data/service/hnp/bin/bash
# test_package/test_spatialite_gui.sh — consumer test for spatialite-gui 2.1.0-beta1.
#
# spatialite_gui is a pure GUI application, which rules out the usual consumer
# test shapes:
#
#   * No --version/--help. Main.cpp:99-115 reads argv[1] as a SQLite database
#     path and immediately constructs MyFrame, so *any* argument — including
#     "--version" — opens a window and blocks. A test running
#     `spatialite_gui --version` would hang CI forever.
#   * It cannot be launched at all on this target. wxwidgets-gtk3/3.2.10's own
#     notes.md records the measured result for its GUI suite: it links but
#     cannot run — "Unable to initialize GTK+, is DISPLAY set properly?"
#     (RC=255) — because the gtk/3.24.43 artifact is broadway-only and there is
#     no broadwayd runtime on the device. That verdict carries over to any
#     wxGTK3 app linked against it, so asserting a successful launch here would
#     assert something already known to be false.
#
# So the contract enforced is the artifact contract: the packaged executable is
# a genuinely native, signed, fully-linked OHOS binary that the SpatiaLite stack
# was really wired into. Each assertion gates a defect that has actually
# occurred on this platform — an unsigned ELF failing execve, or a declared
# requirement that never reached the link line.
#
# Usage: test_spatialite_gui.sh <path-to-spatialite_gui>
set -euo pipefail

BIN="${1:-}"
if [ -z "$BIN" ]; then
    # Fall back to the conanrun PATH when no path was passed in.
    BIN="$(command -v spatialite_gui || true)"
fi
[ -n "$BIN" ] || { echo "[fail] spatialite_gui not found (no arg and not on PATH)" >&2; exit 1; }

echo "== spatialite-gui 2.1.0-beta1 consumer test =="
echo "  binary:  $BIN"

# ---------------------------------------------------------------- locate ELF tools
# OHOS ships no ldd; llvm-readelf is what this platform provides for ELF work
# (the same tool libspatialite's recipe depends on).
READELF=""
for candidate in llvm-readelf readelf /data/service/hnp/bin/llvm-readelf; do
    if command -v "$candidate" >/dev/null 2>&1; then
        READELF="$candidate"
        break
    fi
done
[ -n "$READELF" ] || {
    echo "[fail] no readelf available: cannot verify the packaged ELF" >&2
    exit 1
}
echo "  readelf: $READELF"

# readelf output lands in files before matching (E569): a mid-pipeline reader
# that exits early (awk 'exit', grep -q) closes the read end while llvm-readelf
# is still writing, and llvm's raw_fd_ostream dies with EPIPE -> exit 74
# (EX_IOERR) — "Error 74 while executing" under conan's set -e, with no [fail]
# line. GNU readelf ignores the write error, which is why local GNU-readelf
# runs never reproduced it. Same assertions, no early-exit pipe in between.
TMPDIR_ELF="${TMPDIR:-/tmp}"
EH_FILE="$(mktemp "$TMPDIR_ELF/spgui-elfh-XXXXXX")" || {
    echo "[fail] mktemp in $TMPDIR_ELF failed" >&2; exit 1; }
ES_FILE="$(mktemp "$TMPDIR_ELF/spgui-elfs-XXXXXX")" || {
    rm -f "$EH_FILE"; echo "[fail] mktemp in $TMPDIR_ELF failed" >&2; exit 1; }
ED_FILE="$(mktemp "$TMPDIR_ELF/spgui-elfd-XXXXXX")" || {
    rm -f "$EH_FILE" "$ES_FILE"; echo "[fail] mktemp in $TMPDIR_ELF failed" >&2; exit 1; }
trap 'rm -f "$EH_FILE" "$ES_FILE" "$ED_FILE" 2>/dev/null' EXIT

# ---------------------------------------------------------------- assertion 1
# Packaged and executable.
[ -f "$BIN" ] && [ -s "$BIN" ] || {
    echo "[fail] packaged binary is missing or empty" >&2
    exit 1
}
[ -x "$BIN" ] || { echo "[fail] packaged binary is not executable" >&2; exit 1; }
echo "  [1/6] binary present, non-empty, executable"

# ---------------------------------------------------------------- assertion 2
# OHOS-native AArch64 executable ELF, not a host-arch build leftover.
"$READELF" -h "$BIN" > "$EH_FILE" 2>/dev/null || {
    echo "[fail] readelf -h failed (rc=$?)" >&2
    exit 1
}
MACHINE="$(awk '$1=="Machine:"{print $2; exit}' "$EH_FILE")"
[ "$MACHINE" = "AArch64" ] || {
    echo "[fail] expected AArch64 ELF, readelf reports Machine='${MACHINE:-<none>}'" >&2
    exit 1
}
ELF_TYPE="$(awk '$1=="Type:"{print $2; exit}' "$EH_FILE")"
case "$ELF_TYPE" in
    EXEC|DYN) ;;
    *) echo "[fail] not an executable ELF image (Type='${ELF_TYPE:-<none>}')" >&2; exit 1 ;;
esac
echo "  [2/6] native AArch64 executable ELF (Type=$ELF_TYPE)"

# ---------------------------------------------------------------- assertion 3
# Carries the OHOS code signature. Without a .codesign section execve fails at
# run time even though the file links and reads as a valid ELF — the exact
# failure the conftest signing wrapper exists to prevent, asserted here on the
# deliverable itself.
"$READELF" -S "$BIN" > "$ES_FILE" 2>/dev/null || {
    echo "[fail] readelf -S failed (rc=$?)" >&2
    exit 1
}
if grep -q '\.codesign' "$ES_FILE"; then
    echo "  [3/6] .codesign section present"
else
    echo "[fail] no .codesign section: the binary would fail to exec on device" >&2
    exit 1
fi

# ---------------------------------------------------------------- assertion 4
# The SpatiaLite stack actually reached the link line. A GUI app prints nothing
# on stdout, so DT_NEEDED is the only observable proof that requirements() were
# honoured rather than merely declared.
"$READELF" -d "$BIN" > "$ED_FILE" 2>/dev/null || {
    echo "[fail] readelf -d failed (rc=$?)" >&2
    exit 1
}
NEEDED="$(sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p' "$ED_FILE")"
[ -n "$NEEDED" ] || {
    echo "[fail] no DT_NEEDED entries: the binary links nothing" >&2
    exit 1
}
echo "  linked objects:"
echo "$NEEDED" | sed 's/^/    /'
# liblzma is deliberately absent from this list (fix#11): the GUI never calls
# an lzma_* symbol directly (QueryView.cpp only compares rl2_* SQL function
# *names* as strings), so ld.lld's default --as-needed drops -llzma from the
# link line even though config.log records LIBLZMA_LIBS with -llzma, and no
# object in the closure carries a liblzma.so.5 DT_NEEDED (libspatialite.so /
# librasterlite2.so verified: NEEDED lists have no lzma entry). Requiring it
# here would assert something the toolchain semantics make false by design.
for lib in libspatialite librasterlite2 libgeos_c libproj libcurl libsqlite3; do
    if echo "$NEEDED" | grep -q -- "$lib"; then
        echo "        linked against $lib"
    else
        echo "[fail] $lib absent from DT_NEEDED: a declared requirement never reached the link line" >&2
        exit 1
    fi
done
echo "  [4/6] all 6 required SpatiaLite-stack libraries are linked"

# ---------------------------------------------------------------- assertion 5
# Every NEEDED object resolves at run time. Listing a library is not the same
# as being able to load it: an unsatisfiable DT_NEEDED fails at exec with 127.
SEARCH_DIRS="${SG_LIB_DIR:-${LD_LIBRARY_PATH:-}}"
missing=""
for so in $NEEDED; do
    case "$so" in
        # Platform runtime libraries: resolved by the loader from the system
        # default path (/system/lib64), never shipped inside conan packages.
        # libc++_shared.so verified present on device (fix#11).
        linux-vdso*|libc.so*|libm.so*|libdl.so*|libpthread.so*|librt.so*|libc++_shared.so*) continue ;;
    esac
    found=0
    for dir in $(echo "$SEARCH_DIRS" | tr ':' ' '); do
        [ -n "$dir" ] || continue
        [ -e "$dir/$so" ] && { found=1; break; }
    done
    [ "$found" -eq 1 ] || missing="$missing $so"
done
if [ -n "$missing" ]; then
    echo "[fail] unresolvable shared objects:$missing" >&2
    echo "       searched: $SEARCH_DIRS" >&2
    exit 1
fi
echo "  [5/6] every non-libc DT_NEEDED resolves under the conanrun library path"

# ---------------------------------------------------------------- assertion 6
# The real GUI entry point is linked. A stub that never reached MyFrame would
# still pass 1-5; Main.cpp:108 hands this exact string to wxFrame, so its
# presence proves the wxWidgets frame constructor was compiled and linked in.
# Encoding note (fix#11): wxString's wxT() expands to wchar_t in this wx
# build, so the literal is stored UTF-32-LE in .rodata (device-verified:
# `('a GUI tool...').encode('utf-32-le')` is present, the 8-bit form is not) —
# a plain 8-bit grep can never find it in this build.
# Tool note (fix#18): the wide-char form used to be matched with
# `strings -e L`, which silently depends on *GNU binutils* strings. On the CI
# worker the base PATH is /data/app/bin:/system/bin:/system/sbin:/vendor/bin:…,
# so `strings` resolves to /system/bin/strings = toybox 0.8.12, which rejects
# -e ("Unknown option 'e'"). The 2>/dev/null swallowed that error, the branch
# produced empty output, and assertion 6 failed there (CI #89059) while passing
# locally (where GNU strings, /data/service/hnp/bin/strings, won the PATH race).
# Decouple from strings entirely: drop the NUL bytes with tr so the UTF-32-LE
# (or UTF-16-LE) literal becomes a contiguous ASCII run, then grep it. This is
# encoding-agnostic and uses only tools assertions 1-5 already exercise (tr,
# grep). Deleting NULs cannot fabricate a 30-char literal, so the check is not
# weakened — presence of the exact title string still proves the real wxFrame
# entry point was compiled and linked, not a stub.
GUI_TITLE="a GUI tool for SQLite/SpatiaLite"
# Do NOT use grep -q on the tr pipe: -q exits at the first match, tr then dies
# with SIGPIPE on the closed pipe, and with `set -o pipefail` the pipeline
# fails even though the match was found (same class as the strings rc=141
# measured in fix#12). Plain grep + >/dev/null drains the pipe, so tr exits 0.
if grep -qa "$GUI_TITLE" "$BIN" \
   || tr -d '\000' < "$BIN" | grep -a "$GUI_TITLE" >/dev/null; then
    echo "  [6/6] GUI frame title present: the real wxFrame entry point is linked"
else
    echo "[fail] GUI frame title string missing: wxFrame construction was not linked" >&2
    exit 1
fi

echo "== OK: 11 assertions passed =="
