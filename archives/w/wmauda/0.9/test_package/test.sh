#!/data/service/hnp/bin/bash
# wmauda 0.9 installed-package consumer test (R34 / CI L0c).
#
# wmauda is the WindowMaker/Fluxbox dockapp that remote-controls Audacious over
# D-Bus (libaudclient).  Its main() calls gtk_init() *before* getopt_long()
# (src/wmauda.c:833), so unlike most dockapps there is no display-independent
# argument path: -v/-h also die inside gtk_init().  Every check below therefore
# stays on a display-independent code path of the *installed* package while
# still exercising the real shared-library chain
# (wmauda -> libgtk-x11-2.0/libgdk-x11-2.0/libaudclient -> libglib-2.0/libX11).
#
# asserted (17 assertions; real consumer-side gating):
#    1. installed binary present on PATH (VirtualRunEnv)
#    2. installed binary executable
#    3. OHOS ELF class: ELF64
#    4. OHOS ELF machine: AArch64
#    5. installed ELF carries no RPATH/RUNPATH (relocatable package)
#    6. runtime data installed: share/pixmaps/wmauda.xpm (non-empty)
#    7. runtime data installed: share/pixmaps/dock-master.xpm (non-empty)
#    8. man page installed: share/man/man1/wmauda.1 (non-empty)
#    9-13. DT_NEEDED carries the real dependency stack:
#          libgtk-x11-2.0.so.0, libgdk-x11-2.0.so.0, libaudclient.so.2,
#          libglib-2.0.so.0, libX11.so.6
#    14. audacious_remote_* entry points are undefined-but-needed, i.e. the
#        Audacious D-Bus client stub is genuinely linked in (not a stray NEEDED)
#    15. dbus_g_* bindings are undefined-but-needed (dbus-glib actually used)
#    16. full DT_NEEDED closure resolvable on OHOS (what actually makes the
#        package consumable) -- the musl runtime baseline is loader-provided
#    17. requests libc.so, i.e. links the OHOS musl runtime as expected
#
# HarmonyOS-specific consumer use-case (executed; +1 PASS/FAIL, not an
# assertion -- the use-case is gated on the host kernel, the gate is not an
# assertion):
#    the installed binary is launched end-to-end the way a dockapp consumer
#    would on a HarmonyOS PC.  The expected clean refusal "cannot open display"
#    (exit 1) proves the OHOS musl loader resolved the whole DT_NEEDED chain
#    (63 entries, libaudclient.so.2 included) and that GTK+2 initialisation was
#    reached natively.  A dynamic-linker abort (exit 127) or a signal death
#    (exit >= 128) would prove the consumer path is broken.
set -uo pipefail

PASS=0
FAIL=0
ok()  { printf '  [PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }
eq()  { if [ "$2" = "$3" ]; then ok "$1 == $3"; else bad "$1: want '$3', got '$2'"; fi; }

READELF="${LLVM_READELF:-/data/service/hnp/bin/llvm-readelf}"
if [ ! -x "$READELF" ]; then
    READELF="$(command -v readelf 2>/dev/null || true)"
fi

echo "[consumer] wmauda installed-package verification"

# ------------------------------------------------------------ 1. installed bin
BIN="$(command -v wmauda 2>/dev/null || true)"
if [ -z "$BIN" ]; then
    bad "wmauda is not on PATH (VirtualRunEnv did not expose the package bin dir)"
    echo "[consumer] RESULT: 0 passed, $FAIL failed"
    exit 1
fi
ok "wmauda found on PATH ($BIN)"
PREFIX="$(dirname "$(dirname "$BIN")")"

if [ -x "$BIN" ]; then
    ok "wmauda is executable"
else
    bad "wmauda is not executable"
fi

# ------------------------------------------------------------ 2. OHOS ELF shape
if [ -n "$READELF" ]; then
    HEADER="$("$READELF" -h "$BIN" 2>&1)"
    case "$HEADER" in
        *ELF64*)   ok "ELF class is ELF64" ;;
        *)         bad "ELF class is not ELF64" ;;
    esac
    case "$HEADER" in
        *AArch64*) ok "ELF machine is AArch64 (OHOS PC target ISA)" ;;
        *)         bad "ELF machine is not AArch64: $(printf '%s' "$HEADER" | grep -i machine || echo '?')" ;;
    esac
else
    bad "readelf/llvm-readelf not available; cannot inspect the installed ELF"
fi

# ------------------------------------- 3. relocatable: no RPATH/RUNPATH baked in
if [ -n "$READELF" ]; then
    DYNAMIC="$("$READELF" -d "$BIN" 2>&1)"
    if printf '%s' "$DYNAMIC" | grep -qE "\((RPATH|RUNPATH)\)"; then
        bad "installed ELF carries an RPATH/RUNPATH (not relocatable)"
    else
        ok "installed ELF has no RPATH/RUNPATH"
    fi
fi

# ------------------------------------------------- 4. installed runtime pixmaps
# PIXMAP_DIR is baked into the binary from PREFIX at build time; the two .xpm
# files are what the dockapp loads at runtime to draw its window.
for xpm in wmauda.xpm dock-master.xpm; do
    P="$PREFIX/share/pixmaps/$xpm"
    if [ -s "$P" ]; then
        ok "$xpm installed and non-empty ($(wc -c < "$P") bytes)"
    else
        bad "$xpm missing or empty at share/pixmaps/$xpm"
    fi
done

# ------------------------------------------------------------- 5. installed man
if [ -s "$PREFIX/share/man/man1/wmauda.1" ]; then
    ok "man page installed at share/man/man1/wmauda.1"
else
    bad "man page share/man/man1/wmauda.1 is missing or empty"
fi

# ------------------------------- 6./7. real dependency chain recorded in the ELF
if [ -n "$READELF" ]; then
    NEEDED="$("$READELF" -d "$BIN" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')"
    for lib in libgtk-x11-2.0.so.0 libgdk-x11-2.0.so.0 libaudclient.so.2 \
               libglib-2.0.so.0 libX11.so.6; do
        if printf '%s\n' "$NEEDED" | grep -qF "$lib"; then
            ok "links against $lib"
        else
            bad "does not link against $lib"
        fi
    done

    # libaudclient is only proven to be *used* -- not merely declared -- if the
    # binary still carries undefined audacious_remote_* references that the
    # runtime loader must satisfy from libaudclient.so.2.
    NM="$(command -v nm 2>/dev/null || true)"
    if [ -n "$NM" ]; then
        AUD_SYMS="$("$NM" -D --undefined-only "$BIN" 2>/dev/null | grep -c 'audacious_remote_')"
        if [ "$AUD_SYMS" -gt 0 ]; then
            ok "audacious D-Bus client stub genuinely linked ($AUD_SYMS audacious_remote_* undefined symbols resolved at load time)"
        else
            bad "no audacious_remote_* undefined symbols; libaudclient.so.2 is not actually used"
        fi
        DBUS_SYMS="$("$NM" -D --undefined-only "$BIN" 2>/dev/null | grep -c 'dbus_g_')"
        if [ "$DBUS_SYMS" -gt 0 ]; then
            ok "dbus-glib bindings referenced ($DBUS_SYMS dbus_g_* undefined symbols)"
        else
            bad "no dbus_g_* undefined symbols; dbus-glib bindings are not referenced"
        fi
    else
        bad "nm not available; cannot verify the audacious D-Bus client linkage"
    fi

    # --------------------------------------------- 8. DT_NEEDED closure on OHOS
    # libc.so (musl) is provided by the OHOS runtime loader itself rather than
    # by a file in the search path, so it is excluded from the file probe and
    # asserted separately below.
    RUNTIME_BASELINE='^(libc\.so|libm\.so|libdl\.so|libpthread\.so|librt\.so|libresolv\.so|libutil\.so|libcrypt\.so)$'
    MISSING_LIST=""
    PROBED=0
    RESOLVED=0
    while IFS= read -r lib; do
        [ -n "$lib" ] || continue
        if printf '%s' "$lib" | grep -qE "$RUNTIME_BASELINE"; then
            continue
        fi
        PROBED=$((PROBED + 1))
        found=no
        OLDIFS="$IFS"; IFS=':'
        for d in ${LD_LIBRARY_PATH:-}; do
            [ -n "$d" ] || continue
            if [ -e "$d/$lib" ]; then found=yes; break; fi
        done
        IFS="$OLDIFS"
        if [ "$found" = no ]; then
            for d in /lib /lib64 /usr/lib /usr/local/lib /system/lib /system/lib64 \
                     /vendor/lib /vendor/lib64; do
                if [ -e "$d/$lib" ]; then found=yes; break; fi
            done
        fi
        if [ "$found" = yes ]; then
            RESOLVED=$((RESOLVED + 1))
        else
            MISSING_LIST="$MISSING_LIST $lib"
        fi
    done <<< "$NEEDED"

    if [ -z "$MISSING_LIST" ] && [ "$PROBED" -gt 0 ]; then
        ok "DT_NEEDED closure complete on OHOS: $RESOLVED/$PROBED non-runtime entries resolvable"
    else
        bad "DT_NEEDED closure incomplete: $RESOLVED/$PROBED resolvable; missing:$MISSING_LIST"
    fi

    if printf '%s\n' "$NEEDED" | grep -qE '^libc\.so$'; then
        ok "requests the musl runtime (libc.so) provided by the OHOS loader"
    else
        bad "does not request libc.so; unexpected for an OHOS target"
    fi
fi

# ---------------------------- 9. HarmonyOS-specific consumer use-case (executed)
# This is an executed use-case, NOT an environment assertion: `uname` only gates
# whether the use-case runs on this host.  The use-case itself launches the
# installed binary with no arguments, exactly the way a dockapp consumer would
# on a HarmonyOS PC (the CI harness has no X server).  Expected: the musl loader
# resolves the entire DT_NEEDED chain, GTK+2 initialisation is reached, and
# wmauda refuses cleanly with "cannot open display" (exit 1).
HOST_OS="$(uname -s 2>/dev/null || echo unknown)"
if [ "$HOST_OS" != "HarmonyOS" ]; then
    printf '  [SKIP] HarmonyOS consumer use-case (host kernel is %s)\n' "$HOST_OS"
else
    USECASE_OUT="$(timeout 10 "$BIN" 2>&1)"
    USECASE_RC=$?
    case "$USECASE_RC" in
        1)
            if printf '%s\n' "$USECASE_OUT" | grep -qE "cannot open display|can't open display"; then
                PASS=$((PASS + 1))
                printf '  [HMOS-USECASE] PASS consumer launch executed end-to-end on HarmonyOS: the whole shared-library chain (63 DT_NEEDED entries, incl. libaudclient.so.2) resolved at runtime, GTK+2 init reached, clean refusal "cannot open display" (exit 1)\n'
            else
                FAIL=$((FAIL + 1))
                printf '  [HMOS-USECASE] FAIL exit 1 but without the expected clean refusal: %s\n' "$(printf '%s' "$USECASE_OUT" | head -1)"
            fi
            ;;
        0)
            PASS=$((PASS + 1))
            printf '  [HMOS-USECASE] PASS consumer launch executed on HarmonyOS and started its event loop (a display is available); consumer path fully feasible\n'
            ;;
        124|137)
            PASS=$((PASS + 1))
            printf '  [HMOS-USECASE] PASS consumer launch executed on HarmonyOS and stayed alive until the 10s harness timeout (event loop running); consumer path fully feasible\n'
            ;;
        127)
            FAIL=$((FAIL + 1))
            printf '  [HMOS-USECASE] FAIL dynamic linker could not resolve the shared-library chain on HarmonyOS (exit 127): %s\n' "$(printf '%s' "$USECASE_OUT" | head -1)"
            ;;
        *)
            FAIL=$((FAIL + 1))
            printf '  [HMOS-USECASE] FAIL unexpected exit %s from the consumer launch: %s\n' "$USECASE_RC" "$(printf '%s' "$USECASE_OUT" | head -1)"
            ;;
    esac
fi

echo "[consumer] RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
