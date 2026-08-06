#!/usr/bin/env bash
# R34: real smoke test for git-secrets 1.3.0 — exercises the packaged artifact.
# git-secrets is a bash script that uses git's option parser.
# --help exits with code 129 (git usage convention), so we check output not exit code.
# Using set -uo pipefail (no set -e: we use FAIL counter to run all checks)
set -uo pipefail

BIN_DIR="${1:?usage: test_git_secrets.sh <package bin dir>}"

FAIL=0

# 1. Check script exists and is executable
if [ ! -x "$BIN_DIR/git-secrets" ]; then
    echo "        [fail] git-secrets missing or not executable in $BIN_DIR"
    FAIL=1
fi

GIT_SECRETS="$BIN_DIR/git-secrets"

# 2. Check shebang is bash
if [ -f "$GIT_SECRETS" ]; then
    SHEBANG=$(head -1 "$GIT_SECRETS")
    if [[ "$SHEBANG" != *bash* ]]; then
        echo "        [fail] unexpected shebang: $SHEBANG"
        FAIL=1
    fi
    # 3. Bash syntax check
    if ! bash -n "$GIT_SECRETS"; then
        echo "        [fail] git-secrets bash syntax check failed"
        FAIL=1
    fi
    # 4. Functional test: --help should print usage (exit 129 is git's convention for usage)
    OUTPUT=$("$GIT_SECRETS" --help 2>&1 || true)
    if echo "$OUTPUT" | grep -q "usage: git secrets"; then
        echo "        [ok] git-secrets --help: usage output correct"
    else
        echo "        [fail] git-secrets --help did not produce expected usage output"
        FAIL=1
    fi
fi

if [ "$FAIL" -eq 0 ]; then
    echo "        [ok] git-secrets smoke test: OK"
fi
exit "$FAIL"
