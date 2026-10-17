#!/bin/sh
# Consumer runtime test for the packaged xdx binary (R34 anti-stub).
#
# Runs under the conanrun environment (packaged bin/ on PATH, every
# dependency lib/ dir on LD_LIBRARY_PATH).  POSIX sh only (no bashisms).
#
# Two execution models (told apart by the ELF header, see conanfile.py):
#   native   — the aarch64 ELF matches the host (the CI OpenHarmony worker):
#              exec it directly.
#   emulated — x86_64 dev box: exec it through qemu-aarch64 against the OHOS
#              guest sysroot with the guest-side shims preloaded (the box's
#              own aarch64 loader/libc is absent or incomplete).
#
# Environment (emulated model only, set by test_package/conanfile.py):
#   XD_RUNNER         path to qemu-aarch64
#   XD_GUEST_ROOT     guest sysroot root (qemu -L)
#   XD_GUEST_PRELOAD  colon-separated guest-side shims (qemu -E LD_PRELOAD)
#   XD_CROSS_EMULATED "1"
set -u

xdx_bin="$(command -v xdx)" || {
    echo "[test] FAIL: xdx not found on PATH (package bin/ missing?)"
    exit 1
}
echo "[test] runtime: using $xdx_bin"

# ── Bounded launch: the loader must resolve every DT_NEEDED entry ──
out="$(mktemp)" || { echo "[test] FAIL: mktemp"; exit 1; }
if [ -n "${XD_RUNNER:-}" ]; then
    # -E keeps LD_PRELOAD out of qemu's own environment: an exported
    # LD_PRELOAD would also hit host x86_64 children, which cannot load the
    # aarch64 shims.
    eval "$XD_RUNNER -L \"$XD_GUEST_ROOT\" -E QEMU_LD_PREFIX=\"$XD_GUEST_ROOT\" -E LD_PRELOAD=\"$XD_GUEST_PRELOAD\" \"$xdx_bin\" > \"$out\" 2>&1 &"
else
    "$xdx_bin" > "$out" 2>&1 &
fi
pid=$!
i=0
while [ $i -lt 5 ]; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
    i=$((i + 1))
done

if kill -0 "$pid" 2>/dev/null; then
    # Still in the GTK main loop (a display is available): bounded stop.
    kill -TERM "$pid" 2>/dev/null
    wait "$pid"
    rc=$?
    echo "[test] xdx entered the GTK main loop; TERM rc=$rc"
    case "$rc" in
        0 | 1 | 143) : ;;
        *)
            echo "[test] FAIL: unclean termination rc=$rc"
            cat "$out"
            rm -f "$out"
            exit 1
            ;;
    esac
else
    wait "$pid"
    rc=$?
    echo "[test] xdx exited on its own rc=$rc (headless gtk_init path)"
    case "$rc" in
        0 | 1) : ;;
        *)
            echo "[test] FAIL: unexpected exit rc=$rc"
            cat "$out"
            rm -f "$out"
            exit 1
            ;;
    esac
fi

# Dynamic-loader failures (missing dependency .so or unresolved symbol)
# abort the process before main() with one of these messages — that is a
# genuine consumer failure in both execution models.
if grep -q "Error loading shared library\|cannot open shared object file\|error while loading shared libraries\|symbol lookup error\|Error relocating" "$out"; then
    echo "[test] FAIL: dynamic loader errors in output:"
    cat "$out"
    rm -f "$out"
    exit 1
fi

rm -f "$out"
echo "[test] OK runtime: all dependencies resolved; launch path clean"
echo "[test] xdx consumer test: ALL PASS"
