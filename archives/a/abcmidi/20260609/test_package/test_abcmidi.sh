#!/bin/sh
set -eu

package_folder="$1"
bin_dir="$package_folder/bin"

for program in abc2midi midi2abc abc2abc mftext yaps midicopy abcmatch midistats; do
    test -x "$bin_dir/$program"
done

work_dir="${TMPDIR:-/tmp}/abcmidi-test-$$"
mkdir -p "$work_dir"
trap 'rm -rf "$work_dir"' EXIT

cat >"$work_dir/input.abc" <<'EOF'
X:1
T:HarmonyOS test
M:4/4
L:1/4
K:C
C D E F|G A B c|
EOF

"$bin_dir/abc2midi" "$work_dir/input.abc" -o "$work_dir/output.mid"
test -s "$work_dir/output.mid"
"$bin_dir/midi2abc" "$work_dir/output.mid" -o "$work_dir/roundtrip.abc"
test -s "$work_dir/roundtrip.abc"

echo "abcmidi packaged executables and ABC/MIDI round trip passed"
