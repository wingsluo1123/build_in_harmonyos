#!/bin/sh
# Standalone reproduction of the vcprompt 1.3.0 consumer assertions.
#
# The Conan test_package (conanfile.py, method test()) is what CI executes.
# This script performs the same four assertions by hand, which is useful when
# debugging a device build without re-running `conan create`:
#
#   ./test.sh /path/to/package/bin        # or: ./test.sh "$(dirname "$(command -v vcprompt)")"
#
# Exit code 0 = all assertions passed, non-zero = first failing assertion.
set -eu

bindir="${1:-}"
if [ -z "$bindir" ]; then
    echo "usage: $0 <directory containing the packaged vcprompt>" >&2
    exit 2
fi

vcprompt="$bindir/vcprompt"
if [ ! -x "$vcprompt" ]; then
    echo "FAIL: packaged vcprompt executable not found or not executable: $vcprompt" >&2
    exit 1
fi

branch="ohos-vcprompt-test"
vcs_name="git"
# Scratch tree must not live inside a git checkout: vcprompt walks upwards, so a
# fixture under this repository would report the repository's own branch instead
# of empty output for the "no working copy" case.
workdir="$(mktemp -d "${TMPDIR:-/tmp}/vcprompt-consumer-XXXXXX")"
# Same layout as test_package/conanfile.py: the fake working copy lives in its
# own subdirectory, so no ancestor of no-vc/nested carries VCS metadata.
fixture="$workdir/fixture"
mkdir -p "$fixture/.git/refs/heads" "$workdir/no-vc/nested"
printf 'ref: refs/heads/%s\n' "$branch" > "$fixture/.git/HEAD"
: > "$workdir/no-vc/nested/file.txt"

cleanup() { rm -rf "$workdir"; }
trap cleanup 0 1 2 15

fail=0
assert_eq() {
    label="$1"; expected="$2"; actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "pass: $label"
    else
        echo "fail: $label: expected '$expected', got '$actual'" >&2
        fail=1
    fi
}

# 1. explicit format inside a git working copy
actual=$(cd "$fixture" && "$vcprompt" -f '%n:%b')
assert_eq "explicit format %n:%b" "$vcs_name:$branch" "$actual"

# 2. default format still carries the branch
actual=$(cd "$fixture" && "$vcprompt")
case "$actual" in
    *"$branch"*) echo "pass: default format ($actual)" ;;
    *) echo "fail: default format lost branch info: '$actual'" >&2; fail=1 ;;
esac

# 3. feature list matches the --with-sqlite3=no build
#    `vcprompt -F` prints one feature per line and is captured with trailing
#    newlines stripped, so membership is tested line by line instead of by
#    padding the whole capture with spaces (which only works for single-line
#    output).  tr keeps this portable for any POSIX shell.
features=$(cd "$fixture" && "$vcprompt" -F | tr '\n' ' ')
for required in git hg cvs fossil svn-1.6; do
    case " $features " in
        *" $required "*) echo "pass: feature $required" ;;
        *) echo "fail: feature list is missing $required: [$features]" >&2; fail=1 ;;
    esac
done
for unexpected in svn-1.7 svn-1.8; do
    case " $features " in
        *" $unexpected "*) echo "fail: feature $unexpected present although sqlite3 is disabled" >&2; fail=1 ;;
        *) echo "pass: feature $unexpected absent" ;;
    esac
done

# 4. no version control anywhere above the directory
actual=$(cd "$workdir/no-vc/nested" && "$vcprompt" -f '%n:%b')
assert_eq "no working copy" "" "$actual"

if [ "$fail" -ne 0 ]; then
    echo "vcprompt consumer assertions FAILED" >&2
    exit 1
fi
echo "vcprompt consumer assertions passed"
