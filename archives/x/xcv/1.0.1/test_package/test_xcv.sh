#!/usr/bin/env bash
# Consumer test for the installed xcv script: drives a real cut/copy/paste workflow
# with a throw-away HOME (xcv wipes $HOME/.xcv, never run it against a real HOME).
# Usage: bash test_xcv.sh /path/to/installed/bin/xcv
set -u

XCV=${1:?usage: test_xcv.sh <path-to-xcv>}
fail() { echo "FAIL: $*" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/xcv-test.XXXXXX") || fail "mktemp"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
mkdir -p "$HOME" "$TMP/src/c" "$TMP/dst1" "$TMP/dst2" "$TMP/shim"

printf 'alpha\n' > "$TMP/src/a.txt"
printf 'bravo\n' > "$TMP/src/b.txt"
printf 'hidden\n' > "$TMP/src/.dot"
printf 'delta\n' > "$TMP/src/c/d.txt"

# T1: installed script keeps the adapted shebang and runs through PATH lookup
# (no /bin/bash needed): resolve `bash` from a private PATH entry and exec directly.
head -n1 "$XCV" | grep -qx '#!/usr/bin/env bash' || fail "T1 shebang not adapted"
ln -s "$BASH" "$TMP/shim/bash"
out=$(PATH="$TMP/shim:$PATH" "$XCV" 2>&1) || fail "T1 direct exec of xcv failed"
case $out in *"Usage: \$ xcv <x|c|v|l>"*) ;; *) fail "T1 usage text missing: $out" ;; esac
echo "OK T1: shebang resolved via PATH, usage printed"

# T2: missing options is reported on stderr
err=$("$BASH" "$XCV" c 2>&1 >/dev/null)
case $err in *"Error Copying: not enough options"*) ;; *) fail "T2 error text: $err" ;; esac
echo "OK T2: 'xcv c' without operands rejected"

# T3: copy a tree (incl. dotfile and subdir), list it, paste elsewhere, byte-compare
(cd "$TMP/src" && "$BASH" "$XCV" c -R .) || fail "T3 copy failed"
listing=$("$BASH" "$XCV" l -A) || fail "T3 list failed"
for n in a.txt b.txt .dot c; do
  case $listing in *"$n"*) ;; *) fail "T3 '$n' not listed: $listing" ;; esac
done
(cd "$TMP/dst1" && "$BASH" "$XCV" v) || fail "T3 paste failed"
for f in a.txt b.txt .dot c/d.txt; do
  cmp -s "$TMP/src/$f" "$TMP/dst1/$f" || fail "T3 content mismatch for $f"
done
[ -z "$("$BASH" "$XCV" l -A)" ] || fail "T3 staging not emptied after paste"
echo "OK T3: copy -> list -> paste round trip preserved all files"

# T4: cut removes the source and pasting restores the exact bytes
(cd "$TMP/src" && "$BASH" "$XCV" x a.txt b.txt) || fail "T4 cut failed"
[ ! -e "$TMP/src/a.txt" ] && [ ! -e "$TMP/src/b.txt" ] || fail "T4 sources not removed"
(cd "$TMP/dst2" && "$BASH" "$XCV" v) || fail "T4 paste failed"
[ "$(cat "$TMP/dst2/a.txt")" = alpha ] && [ "$(cat "$TMP/dst2/b.txt")" = bravo ] || fail "T4 pasted content wrong"
echo "OK T4: cut -> paste moved files intact"

# T5: a new copy/cut replaces what was staged before
printf 'one\n' > "$TMP/one.txt"; printf 'two\n' > "$TMP/two.txt"
"$BASH" "$XCV" c "$TMP/one.txt" || fail "T5 first copy"
"$BASH" "$XCV" c "$TMP/two.txt" || fail "T5 second copy"
[ "$("$BASH" "$XCV" l)" = two.txt ] || fail "T5 staging should hold only two.txt"
echo "OK T5: staging replaced by latest copy"

# T6: everything stays inside the temporary HOME
[ -d "$HOME/.xcv" ] || fail "T6 staging dir not under test HOME"
echo "OK T6: staging dir lives in \$HOME/.xcv of the test HOME"
echo "ALL 6 xcv consumer tests passed"
