#!/bin/sh
# test_semtag_ohos.sh — HarmonyOS-specific runtime assertions for semtag.
#
# Covers what patches/0001-semtag.patch changes (the hnp-bash shebang) and the
# platform behaviours semtag's code paths depend on: the hnp bash must run the
# script's bash-4 features, tag creation must work on an account with no Git
# identity (semtag derives one from `id -u -n` / `hostname`), and the tool must
# not need a writable /tmp. Assertions whose precondition does not hold on the
# current host print SKIP instead of silently passing. Fixtures are written
# with printf, never with here-documents.
#
# Usage: test_semtag_ohos.sh <path-to-semtag> [bash-interpreter]
set -u

# On HarmonyOS the conanrun PATH does not contain the hnp tool dir (bash, git).
PATH="$PATH:/data/service/hnp/bin"
export PATH

SEMTAG="${1:?usage: test_semtag_ohos.sh <path-to-semtag> [bash-interpreter]}"
HNP_BASH=/data/service/hnp/bin/bash
if [ -n "${2:-}" ]; then
    BASH_BIN="$2"
elif [ -x "$HNP_BASH" ]; then
    BASH_BIN="$HNP_BASH"
else
    BASH_BIN=bash
fi

pass=0
fail=0
skip=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1 -- $2"; fail=$((fail + 1)); }
sk() { echo "SKIP: $1 -- $2"; skip=$((skip + 1)); }

WORK="$(pwd)/semtag-tp-ohos"
rm -rf "$WORK"
# Leave no fixture repositories behind in the (versioned) recipe folder.
trap 'cd / && rm -rf "$WORK"' EXIT
mkdir -p "$WORK/home" || { echo "FAIL: cannot create work dir $WORK"; exit 1; }

export HOME="$WORK/home"
export GIT_CONFIG_NOSYSTEM=1
# HMDFS worktrees are owned by another uid: Git refuses them with "detected
# dubious ownership" (E101). safe.directory is only honoured from global/system
# config, so use a private global config instead of /dev/null.
printf '[safe]\n\tdirectory = *\n' > "$HOME/.gitconfig"
export GIT_CONFIG_GLOBAL="$HOME/.gitconfig"
G="git -c user.name=fixture -c user.email=fixture@example.invalid"

# Fixture: one commit tagged v1.2.3, then a second commit (something to tag).
REPO="$WORK/repo"
mkdir -p "$REPO" && cd "$REPO" || exit 1
git init -q . && git symbolic-ref HEAD refs/heads/master || { echo "FAIL: git unusable"; exit 1; }
printf 'a\n' > f && git add f && $G commit -q -m "first commit" && $G tag -a v1.2.3 -m "release 1.2.3"
printf 'b\n' > g && git add g && $G commit -q -m "second commit"
[ -s f ] && [ -s g ] || { echo "FAIL: fixture files are empty (shell could not write them)"; exit 1; }

# ── OHOS-1: packaged shebang points at the hnp bash (E037) ──────────────────
head1=$(head -n 1 "$SEMTAG")
if [ "$head1" = "#!/data/service/hnp/bin/bash" ]; then
    ok "packaged shebang is #!/data/service/hnp/bin/bash"
else
    no "packaged shebang is #!/data/service/hnp/bin/bash" "got '$head1'"
fi

# ── OHOS-2: the shebang interpreter really runs the packaged script ─────────
# Direct execution is tried first. Conan's cache may sit on HMDFS, where exec
# bits are not honoured; then the shebang interpreter itself must still run
# the script, and the PASS line says which path was taken. The script needs
# bash >= 4.3 (associative arrays, namerefs, mapfile, process substitution),
# so a correct answer here also proves the device bash provides them.
if [ -x "$HNP_BASH" ]; then
    out=$(cd "$REPO" && "$SEMTAG" getlast 2>/dev/null)
    if [ "$out" = "v1.2.3" ]; then
        ok "direct execution through the hnp-bash shebang works (getlast=v1.2.3)"
    else
        out2=$(cd "$REPO" && "$HNP_BASH" "$SEMTAG" getlast 2>/dev/null)
        if [ "$out2" = "v1.2.3" ]; then
            ok "hnp bash runs the packaged semtag (direct exec unavailable here: '$out')"
        else
            no "hnp bash runs the packaged semtag" "direct='$out' explicit='$out2'"
        fi
    fi
else
    sk "hnp bash runs the packaged semtag" "$HNP_BASH not present on this host"
fi

# ── OHOS-3: tag creation without any Git identity ───────────────────────────
# On a fresh HarmonyOS account Git has no user.name/user.email. semtag's
# setup_git_user fills them from `id -u -n` and `hostname` before `git tag -a`;
# if either tool is missing or behaves differently the tag is never created.
before_name=$(git config user.name 2>/dev/null || true)
out=$(cd "$REPO" && "$BASH_BIN" "$SEMTAG" final 2>/dev/null)
rc=$?
tagger=$(git for-each-ref refs/tags/v1.2.4 --format='%(taggername)|%(taggeremail)' 2>/dev/null)
uname_cfg=$(git config --local user.name 2>/dev/null || true)
umail_cfg=$(git config --local user.email 2>/dev/null || true)
if [ -z "$before_name" ] && [ "$rc" -eq 0 ] && [ "$out" = "v1.2.4" ] \
    && [ -n "$uname_cfg" ] && echo "$umail_cfg" | grep -q '@.'; then
    ok "final tags v1.2.4 with no preconfigured identity (name='$uname_cfg' email='$umail_cfg')"
else
    no "final tags v1.2.4 with no preconfigured identity" \
        "pre='$before_name' rc=$rc out='$out' name='$uname_cfg' email='$umail_cfg'"
fi
case "$tagger" in
    ?*"|<"?*">") ok "the created tag records a tagger derived from the account ($tagger)" ;;
    *) no "the created tag records a tagger derived from the account" "tagger='$tagger'" ;;
esac

# ── OHOS-4: no writable /tmp required (E002) ────────────────────────────────
# /tmp is read-only on HarmonyOS. semtag only uses command/process
# substitution (pipes), so it must work with TMPDIR pointing nowhere. Also
# runs the full tag-reading path, which is where mapfile + <(...) are used.
out=$(cd "$REPO" && TMPDIR=/nonexistent-semtag-tmp "$BASH_BIN" "$SEMTAG" getfinal 2>/dev/null)
rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "v1.2.4" ]; then
    ok "getfinal works with TMPDIR pointing at a nonexistent dir (no temp files needed)"
else
    no "getfinal works with TMPDIR pointing at a nonexistent dir" "rc=$rc out='$out'"
fi

echo "semtag ohos: $pass passed, $fail failed, $skip skipped"
[ "$fail" -eq 0 ]
