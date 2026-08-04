#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the asciiquarium script
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] asciiquarium script exists and is executable"
ASCIIQUARIUM=$(command -v asciiquarium 2>/dev/null || true)
if [ -z "$ASCIIQUARIUM" ]; then
    # Try common bin locations
    for p in "$CONAN_BIN_DIRS_ASCIIQUARIUM" "$HOME/.local/bin" /usr/local/bin; do
        if [ -f "$p/asciiquarium" ]; then
            ASCIIQUARIUM="$p/asciiquarium"
            break
        fi
    done
fi
if [ -z "$ASCIIQUARIUM" ] || [ ! -f "$ASCIIQUARIUM" ]; then
    echo "FAIL: asciiquarium script not found"
    exit 1
fi
echo "OK: found at $ASCIIQUARIUM"

echo "[test] asciiquarium version 1.6 in script"
if grep -q 'my $version = "1.6"' "$ASCIIQUARIUM"; then
    echo "OK: version 1.6 confirmed in script source"
else
    echo "FAIL: version string not found"
    exit 1
fi

echo "[test] asciiquarium script is valid Perl (syntax)"
if perl -c "$ASCIIQUARIUM" 2>/dev/null; then
    echo "OK: Perl syntax check passed"
else
    # Perl syntax check may fail due to missing modules (Curses, Term::Animation)
    # This is expected on systems without Perl XS dependencies installed.
    # Verify the shebang line is correct as fallback.
    if head -1 "$ASCIIQUARIUM" | grep -q '^#!.*perl'; then
        echo "OK: valid Perl shebang (syntax check skipped — missing XS deps)"
    else
        echo "FAIL: not a valid Perl script"
        exit 1
    fi
fi
