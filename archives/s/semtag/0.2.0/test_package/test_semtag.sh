#!/bin/sh
# test_semtag.sh — generic behaviour of the installed semtag.
#
# Every assertion runs `bash <pkg>/bin/semtag ...` inside a throw-away Git
# repository built here, and checks semtag's observable output / exit code /
# the tags it creates. Fixtures are written with printf, never with
# here-documents (the HarmonyOS device backs them with temp files under the
# read-only /tmp).
#
# Usage: test_semtag.sh <path-to-semtag> [bash-interpreter]
set -u

# On HarmonyOS the conanrun PATH does not contain the hnp tool dir (bash, git).
PATH="$PATH:/data/service/hnp/bin"
export PATH

SEMTAG="${1:?usage: test_semtag.sh <path-to-semtag> [bash-interpreter]}"
if [ -n "${2:-}" ]; then
    BASH_BIN="$2"
elif [ -x /data/service/hnp/bin/bash ]; then
    BASH_BIN=/data/service/hnp/bin/bash
else
    BASH_BIN=bash
fi

pass=0
fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1 -- $2"; fail=$((fail + 1)); }

WORK="$(pwd)/semtag-tp-generic"
rm -rf "$WORK"
# Leave no fixture repositories behind in the (versioned) recipe folder.
trap 'cd / && rm -rf "$WORK"' EXIT
mkdir -p "$WORK/home" || { echo "FAIL: cannot create work dir $WORK"; exit 1; }

# Isolate from any user/system Git configuration.
export HOME="$WORK/home"
export GIT_CONFIG_NOSYSTEM=1
# HMDFS worktrees are owned by another uid: Git refuses them with "detected
# dubious ownership" (E101). safe.directory is only honoured from global/system
# config, so use a private global config instead of /dev/null.
printf '[safe]\n\tdirectory = *\n' > "$HOME/.gitconfig"
export GIT_CONFIG_GLOBAL="$HOME/.gitconfig"
G="git -c user.name=fixture -c user.email=fixture@example.invalid"

# mkrepo <dir>: one commit on master, annotated tag v1.2.3.
mkrepo() {
    mkdir -p "$1" && cd "$1" || return 1
    git init -q . && git symbolic-ref HEAD refs/heads/master || return 1
    printf 'a\n' > f && git add f || return 1
    $G commit -q -m "first commit" || return 1
    $G tag -a v1.2.3 -m "release 1.2.3" || return 1
}

# st <args...>: run semtag; sets STDOUT, OUT (stdout+stderr) and RC.
# Exact comparisons use STDOUT only: on the HarmonyOS device the hnp bash may
# print getcwd diagnostics on stderr when started in an HMDFS directory, which
# must not turn into false failures. Message checks use grep on OUT.
st() {
    STDOUT=$("$BASH_BIN" "$SEMTAG" "$@" 2>"$WORK/stderr.txt")
    RC=$?
    OUT="$STDOUT
$(cat "$WORK/stderr.txt")"
}

expect_out() { # <label> <expected-output> <semtag args...>
    label="$1"; want="$2"; shift 2
    st "$@"
    if [ "$RC" -eq 0 ] && [ "$STDOUT" = "$want" ]; then
        ok "$label"
    else
        no "$label" "rc=$RC out='$STDOUT' want='$want'"
    fi
}

mkrepo "$WORK/r1" || { echo "FAIL: cannot build fixture repo (git unusable?)"; exit 1; }

# 1-2: program metadata.
st --version
if [ "$RC" -eq 0 ] && echo "$STDOUT" | grep -Eq '^semtag: v[0-9]+\.[0-9]+\.[0-9]+$'; then
    ok "--version prints 'semtag: vX.Y.Z'"
else
    no "--version prints 'semtag: vX.Y.Z'" "rc=$RC out='$OUT'"
fi
st --help
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '^Usage:' && echo "$OUT" | grep -q 'getlast'; then
    ok "--help lists usage and commands"
else
    no "--help lists usage and commands" "rc=$RC"
fi

# 3-4: reading tags (final vs. pre-release).
expect_out "getlast returns the newest tag" "v1.2.3" getlast
$G tag -a v1.3.0-rc.1 -m "rc" || no "fixture rc tag" "git tag failed"
expect_out "getlast sees a newer pre-release tag" "v1.3.0-rc.1" getlast
expect_out "getfinal ignores pre-release tags" "v1.2.3" getfinal
git tag -d v1.3.0-rc.1 >/dev/null

# 5-9: version bumping in display-only mode (-o), nothing is tagged.
expect_out "final -s minor -o bumps the minor" "v1.3.0" final -s minor -o
expect_out "final -s major -o bumps the major" "v2.0.0" final -s major -o
expect_out "final -s patch -o -p drops the 'v' prefix" "1.2.4" final -s patch -o -p
expect_out "alpha -o yields a -alpha.1 pre-release" "v1.2.4-alpha.1" alpha -o
expect_out "candidate -o yields a -rc.1 pre-release" "v1.2.4-rc.1" candidate -o

# 10: forced version must be greater than the last one.
st final -v v1.0.0 -o
if [ "$RC" -ne 0 ] && echo "$OUT" | grep -q 'must be greater'; then
    ok "-v with a version lower than the last tag is rejected"
else
    no "-v with a version lower than the last tag is rejected" "rc=$RC out='$OUT'"
fi

# 11: -o must not have created anything.
if [ "$(git tag -l | wc -l | tr -d ' ')" = "1" ]; then
    ok "display-only runs created no tag"
else
    no "display-only runs created no tag" "tags: $(git tag -l | tr '\n' ' ')"
fi

# 12: nothing to tag when there is no commit since the last final version.
st final
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'No commits since last final version' \
    && [ "$(git tag -l | wc -l | tr -d ' ')" = "1" ]; then
    ok "final without new commits creates no tag"
else
    no "final without new commits creates no tag" "rc=$RC out='$OUT'"
fi

# 13-14: real tagging after a new commit.
printf 'b\n' > g && git add g && $G commit -q -m "second commit"
st final
if [ "$RC" -eq 0 ] && [ "$STDOUT" = "v1.2.4" ] && [ "$(git cat-file -t v1.2.4 2>/dev/null)" = "tag" ]; then
    ok "final creates the annotated tag v1.2.4"
else
    no "final creates the annotated tag v1.2.4" "rc=$RC out='$STDOUT' type='$(git cat-file -t v1.2.4 2>&1)'"
fi
if git tag -l -n5 v1.2.4 | grep -q 'second commit'; then
    ok "tag message carries the commit log since the last final version"
else
    no "tag message carries the commit log since the last final version" "$(git tag -l -n5 v1.2.4)"
fi

# 15: getcurrent on a clean, fully tagged tree is the tag itself.
expect_out "getcurrent on a clean tagged tree is the last tag" "v1.2.4" getcurrent

# 16-17: dirty working tree is refused unless forced.
printf 'c\n' >> f
before=$(git tag -l | wc -l | tr -d ' ')
st alpha
after=$(git tag -l | wc -l | tr -d ' ')
if [ "$RC" -ne 0 ] && [ "$before" = "$after" ]; then
    ok "dirty tree: tagging is refused and no tag is created"
else
    no "dirty tree: tagging is refused and no tag is created" "rc=$RC tags $before->$after"
fi
st alpha -f
if [ "$RC" -eq 0 ] && [ "$STDOUT" = "v1.2.5-alpha.1" ] && git rev-parse -q --verify refs/tags/v1.2.5-alpha.1 >/dev/null; then
    ok "alpha -f tags a dirty tree anyway"
else
    no "alpha -f tags a dirty tree anyway" "rc=$RC out='$OUT'"
fi

# 18: unknown command.
st frobnicate
if [ "$RC" -ne 0 ] && echo "$OUT" | grep -q 'is not a valid command'; then
    ok "unknown command is rejected"
else
    no "unknown command is rejected" "rc=$RC out='$OUT'"
fi

echo "semtag generic: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
