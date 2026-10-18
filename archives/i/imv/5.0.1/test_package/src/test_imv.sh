#!/data/service/hnp/bin/bash
# test_package/src/test_imv.sh — consumer test for imv 5.0.1 (OHOS PC / aarch64)
#
# Usage: test_imv.sh <bindir> [wayland_libdir]
#
#   <bindir>          bin/ of the installed imv package
#   [wayland_libdir]  lib/ of the installed wayland dependency (optional; used
#                     by group 3 to work around an external package defect)
#
# Exits non-zero when an assertion fails. Assertion groups are printed so the
# conan log carries the real count.
set -u

BIN_DIR="${1:?usage: test_imv.sh <bindir> [wayland_libdir]}"
WAYLAND_LIB="${2:-}"

IMV="$BIN_DIR/imv"
IMV_MSG="$BIN_DIR/imv-msg"
IMV_DIR="$BIN_DIR/imv-dir"

PASS=0
FAIL=0
SKIP=0

ok()   { echo "  ok    - $1"; PASS=$((PASS + 1)); }
bad()  { echo "  FAIL  - $1"; FAIL=$((FAIL + 1)); }
skip() { echo "  SKIP  - $1"; SKIP=$((SKIP + 1)); }

readelf() { command -v llvm-readelf || echo /data/service/hnp/bin/llvm-readelf; }
objcopy() { command -v llvm-objcopy || echo /data/service/hnp/bin/llvm-objcopy; }
signer()  { command -v binary-sign-tool || echo /data/service/hnp/bin/binary-sign-tool; }

echo "== group 1: run the shipped imv-msg binary =="

if [ ! -x "$IMV_MSG" ]; then
  bad "bin/imv-msg is missing or not executable"
else
  ok "bin/imv-msg exists and is executable"

  out="$("$IMV_MSG" 2>&1)"
  rc=$?
  if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "Usage:"; then
    ok "imv-msg (no args) prints its usage line and exits 0"
  else
    bad "imv-msg (no args) rc=$rc out=$out"
  fi

  out="$("$IMV_MSG" 4194303 quit 2>&1)"
  rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "Failed to connect"; then
    ok "imv-msg (bogus pid) reports the failed AF_UNIX connect and exits non-zero"
  else
    bad "imv-msg (bogus pid) rc=$rc out=$out"
  fi
fi

echo "== group 2: the shipped imv artifact =="

if [ ! -x "$IMV" ]; then
  bad "bin/imv is missing or not executable"
else
  ok "bin/imv exists and is executable"

  # OHOS refuses to exec/mmap an ELF without a valid .codesign; the section is
  # written by binary-sign-tool in package() (meson install rewrote the ELF).
  sig="$("$(readelf)" -S "$IMV" 2>/dev/null | grep -c '\.codesign')"
  if [ "${sig:-0}" -ge 1 ]; then
    ok "bin/imv carries a .codesign section"
  else
    bad "bin/imv has no .codesign section"
  fi

  needed="$("$(readelf)" -d "$IMV" 2>/dev/null | grep NEEDED)"
  for lib in libwayland-client.so.0 libGL.so.1 libpango-1.0.so.0 libcairo.so.2 \
             libxkbcommon.so.0 libwebpdecoder.so.3; do
    if printf '%s' "$needed" | grep -q "$lib"; then
      ok "bin/imv DT_NEEDED contains $lib"
    else
      bad "bin/imv DT_NEEDED is missing $lib"
    fi
  done
fi

if [ -x "$IMV_DIR" ]; then
  ok "bin/imv-dir (contrib-commands) exists and is executable"
else
  bad "bin/imv-dir (contrib-commands) is missing or not executable"
fi

echo "== group 3 (evidence only, NOT deliverable runnability): 外部缺陷复现旁证 =="

echo "  info  - bin/imv is NOT directly runnable in an unpatched environment:"
echo "  info  -   first error = 'Error loading shared library libwayland-cursor.so.0:"
echo "  info  -   (needed by ./imv)' + 'Error relocating ./imv: wl_cursor_theme_destroy:"
echo "  info  -   symbol not found'; dlopen() root cause = EACCES (.codesign 校验失败),"
echo "  info  -   caused by the published wayland package (see notes.md)."

# Two independent environment facts are needed to start bin/imv here, and both
# are disclosed in notes.md / the PR body:
#   (a) the published wayland package ships libwayland-cursor.so.0 with an
#       invalid .codesign -> loading it fails with EACCES ("Permission denied").
#       This script reproduces that first, then re-signs a private copy of that
#       single library and puts it first on the loader path.
#   (b) gl4es' libGL.so.1 initialises in a constructor and segfaults unless
#       LIBGL_GLES/LIBGL_EGL point at the OHOS system GLES/EGL libraries (the
#       gl4es package's own test_package exports exactly these two variables).
#       imv's package_info() exports them as runenv, they are re-exported here
#       so the group also works when the conanrun environment is incomplete.
if [ ! -x "$IMV" ]; then
  skip "bin/imv not executable, cannot run the binary check"
elif [ -z "$WAYLAND_LIB" ] || [ ! -d "$WAYLAND_LIB" ]; then
  skip "wayland libdir not provided, cannot run the binary check"
else
  export LIBGL_GLES="${LIBGL_GLES:-/system/lib64/libGLESv3.so}"
  export LIBGL_EGL="${LIBGL_EGL:-/system/lib64/libEGL.so}"

  cursor="$WAYLAND_LIB/libwayland-cursor.so.0"
  raw_out="$(env -u LD_PRELOAD "$IMV" -h 2>&1 | head -3)"
  if printf '%s' "$raw_out" | grep -q "Permission denied\|Error loading shared library"; then
    echo "  info  - reproduced external defect: $(printf '%s' "$raw_out" | head -1)"
  fi

  work="$(mktemp -d "${TMPDIR:-$HOME}/imv-consume.XXXXXX" 2>/dev/null || echo "$BIN_DIR/../consume-tmp")"
  mkdir -p "$work"
  fixed="$work/libwayland-cursor.so.0"
  if [ -f "$cursor" ] && "$(objcopy)" --remove-section .codesign "$cursor" "$fixed" 2>/dev/null \
     && "$(signer)" sign -inFile "$fixed" -outFile "$fixed.signed" -selfSign 1 >/dev/null 2>&1; then
    mv -f "$fixed.signed" "$fixed"
    out="$(LD_LIBRARY_PATH="$work:${LD_LIBRARY_PATH:-}" "$IMV" -h 2>&1)"
    rc=$?
    if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "imv 5.0.1"; then
      ok "imv -h runs and reports version 5.0.1 (with the external library repaired)"
    else
      bad "imv -h rc=$rc out=$(printf '%s' "$out" | head -3)"
    fi
    backends=0
    for name in farbfeld libheif libjpeg-turbo libnsbmp libnsgif libpng libRSVG libtiff libwebp; do
      if printf '%s' "$out" | grep -q "Name: $name"; then
        backends=$((backends + 1))
      fi
    done
    if [ "$backends" -eq 9 ]; then
      ok "imv -h lists all 9 enabled image backends"
    else
      bad "imv -h lists $backends/9 enabled image backends"
    fi
  else
    skip "cannot build the re-signed libwayland-cursor copy (tools unavailable)"
  fi
  rm -rf "$work" 2>/dev/null || true
fi

echo "== consumer test summary: passed=$PASS failed=$FAIL skipped=$SKIP =="
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
