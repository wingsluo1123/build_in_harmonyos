#!/bin/sh
# test_xlbiff.sh — verify the packaged xlbiff binary on HarmonyOS.
#
# Usage: test_xlbiff.sh <package-folder> <xlbiff-binary> <ld-preload-list>
#
# The device and the CI worker are headless: there is no X server binary in
# the image and no OHOS Xvfb is published on the remote (coolmail/1.3
# precedent), and xlbiff handles -version/-help only AFTER XtVaAppInitialize
# opened the display — no argument path completes headlessly.  The checks
# below still exercise the packaged artifact for real:
#
#   1. the packaged binary exists and is executable (ELF);
#   2. the 4.6.11 version string is compiled into the binary;
#   3. without DISPLAY the program exits non-zero with Xt's
#      "Can't open display" diagnostic: that loads the dynamic chain
#      (libXaw -> libXmu/libXpm, libXt -> libSM/libICE, libX11 ->
#      libxcb/libXau/libXdmcp, libXrandr -> libXrender) and runs the
#      resource parsing at the top of main() before display init fails;
#   4. the installed man pages / app-defaults / helper script exist;
#   5. upstream unittest suite (mailbox-preview-test.py, 9 cases) runs
#      against the *packaged* mailbox-preview helper (headless, 9/9).
#
# POSIX sh only (toybox ash): no set -e/-u, no bashisms. Exit code 126
# means the kernel refused to exec the binary and is always a failure.

pkg=$1
bin=$2
ld_preload_extra="${3:-}"

checks=0

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

ok() {
    checks=$((checks + 1))
    echo "OK: $1"
}

[ -n "$pkg" ] && [ -n "$bin" ] || fail "usage: test_xlbiff.sh <pkg> <binary> <ld-preload>"
[ -f "$bin" ] || fail "packaged xlbiff binary missing: $bin"
[ -x "$bin" ] || fail "packaged xlbiff binary is not executable: $bin"
ok "packaged binary present and executable"

BIN_DIR=$(dirname "$bin")
LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH
if [ -n "$ld_preload_extra" ]; then
    LD_PRELOAD="$ld_preload_extra"
    export LD_PRELOAD
fi

echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

# Diagnostics: musl ldd prints resolution of every DT_NEEDED entry
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$bin" 2>&1 || true
fi

# --- version string compiled in ------------------------------------------------
# xlbiff -version would need a display; the version macro (from AC_INIT)
# is baked into the binary, so grep it there. Prefer `strings | grep`
# (toybox ash environment); fall back to `grep -a` on GNU grep hosts.
ver_found=0
if command -v strings >/dev/null 2>&1; then
    if strings "$bin" | grep -q "4\.6\.11"; then
        ver_found=1
    fi
elif grep -aq "4\.6\.11" "$bin" 2>/dev/null; then
    ver_found=1
fi
if [ "$ver_found" -eq 1 ]; then
    ok "version string 4.6.11 compiled into the binary"
else
    fail "version string 4.6.11 not found in binary"
fi

# --- headless X initialisation path --------------------------------------------
nodisp_out="${TMPDIR:-/tmp}/xlbiff-nodisplay.$$.out"
( unset DISPLAY; "$bin" > "$nodisp_out" 2>&1 )
rc=$?
cat "$nodisp_out"
if [ "$rc" -eq 0 ]; then
    fail "xlbiff reported success without an X display"
fi
if [ "$rc" -eq 126 ]; then
    fail "kernel refused to exec xlbiff (rc=126)"
fi
if ! grep -q "Can't open display" "$nodisp_out"; then
    fail "Xt display diagnostic missing (exit=$rc)"
fi
rm -f "$nodisp_out"
ok "headless run exited $rc after loading the X11/Xt/Xaw chain"

# --- installed resources --------------------------------------------------------
man_page="$pkg/share/man/man1/xlbiff.1"
[ -f "$man_page" ] || fail "man page not installed: $man_page"
ok "xlbiff man page installed"

preview_man="$pkg/share/man/man1/mailbox-preview.1"
[ -f "$preview_man" ] || fail "mailbox-preview man page not installed: $preview_man"
ok "mailbox-preview man page installed"

app_defaults="$pkg/share/X11/app-defaults/XLbiff"
[ -f "$app_defaults" ] || fail "X11 app-defaults resource file not installed: $app_defaults"
ok "X11 app-defaults installed (XLbiff)"

form_file="$pkg/etc/nmh/xlbiff.form"
[ -f "$form_file" ] || fail "xlbiff.form not installed: $form_file"
ok "xlbiff.form installed"

helper="$pkg/bin/mailbox-preview"
[ -f "$helper" ] || fail "mailbox-preview helper script not installed: $helper"
ok "mailbox-preview helper installed"

# --- upstream unittest suite (mailbox-preview-test.py, 9 cases) ----------------
# Upstream ships mailbox-preview-test.py with 9 unittest cases for the
# mailbox-preview parser (EXTRA_DIST in Makefile.am, not wired into
# `make check`). They run headlessly. They are executed here against
# the *packaged* helper script: bin/mailbox-preview is copied to
# <tmpdir>/mailbox-preview.py so importlib.import_module('mailbox-preview')
# resolves (same mechanism as upstream's own test invocation).
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mbtest_dir="${TMPDIR:-/tmp}/xlbiff-mbtest.$$"
mkdir -p "$mbtest_dir" || fail "cannot create mbtest dir: $mbtest_dir"
cp "$pkg/bin/mailbox-preview" "$mbtest_dir/mailbox-preview.py" || fail "cannot copy packaged mailbox-preview"
cp "$script_dir/mailbox-preview-test.py" "$mbtest_dir/mailbox-preview-test.py" || fail "cannot stage upstream unittest"
( cd "$mbtest_dir" && PYTHONPATH="$mbtest_dir${PYTHONPATH:+:$PYTHONPATH}" python3 mailbox-preview-test.py )
mb_rc=$?
rm -rf "$mbtest_dir"
if [ "$mb_rc" -eq 0 ]; then
    ok "upstream unittest suite (mailbox-preview-test.py, 9/9) against packaged helper"
else
    fail "upstream unittest suite failed (rc=$mb_rc)"
fi

echo "xlbiff smoke test OK ($checks checks)"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xlbiff.sh","discovered":%d,"passedCount":%d}\n' \
    "$checks" "$checks"
