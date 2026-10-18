#!/usr/bin/env bash
# Reproduction harness for the kf6-relative-needed knowledge pack.
#
#   ./reproduce.sh off   # SKILL disabled -> conan create must FAIL with the original
#                        #                    "error while loading shared libraries: ../../bin/..."
#   ./reproduce.sh on    # SKILL enabled  -> conan create must PASS
#
# No pipes anywhere (avoids SIGPIPE); every run is redirected to its own log and
# the exit code of conan create is the verdict.  Only the OHOS clang toolchain of
# the project profile (ci/conan/profiles/ohos-aarch64) is used.
set -u

SAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SAMPLE_DIR/../../.." && pwd)"
RECIPE_DIR="$REPO_DIR/archives/b/baloo-widgets/26.04.0"
SKILL_ROOT="${SKILL_ROOT:-$REPO_DIR}"
PROFILE="${PROFILE:-$REPO_DIR/ci/conan/profiles/ohos-aarch64}"
MODE="${1:-}"
OUT_DIR="$SAMPLE_DIR/reports"
LOG="$OUT_DIR/repro-$MODE.log"

mkdir -p "$OUT_DIR"

case "$MODE" in
  off) SHIM=False ;;
  on)  SHIM=True ;;
  *) echo "usage: $0 off|on" >&2; exit 2 ;;
esac

# 1) identification stage: scan the dependency package that carries the relative
#    DT_NEEDED entries (best effort, never fatal).
PKG="$(conan cache path baloo/26.04.3 2>/dev/null)"
if [ -n "${PKG:-}" ] && [ -d "$PKG" ]; then
  python3 "$SAMPLE_DIR/detect-relative-needed.py" --pkg-root "$PKG" \
      > "$OUT_DIR/detect-$MODE.log" 2>&1
  echo "detect exit: $? (log: $OUT_DIR/detect-$MODE.log)"
fi

# 2) sample-library build: the compat shim is created by the recipe only when
#    kb_compat_shim=True.
echo "== repro $MODE (kb_compat_shim=$SHIM) -> $LOG" > "$LOG"
echo "== profile: $PROFILE" >> "$LOG"

conan create "$RECIPE_DIR" \
    --version 26.04.0 \
    --profile:build "$PROFILE" --profile:host "$PROFILE" \
    --build='baloo-widgets/*' \
    --options "&:kb_compat_shim=$SHIM" >> "$LOG" 2>&1
RC=$?
echo "== conan create exit code: $RC" >> "$LOG"

if [ "$MODE" = "off" ]; then
  if grep -qE 'Error loading shared library|error while loading shared libraries|cannot open shared object file' "$LOG"; then
    echo "REPRO OK: original loader error reproduced (log: $LOG)"
    exit 0
  fi
  echo "REPRO FAILED: loader error not reproduced; see $LOG" >&2
  exit 1
fi

if [ "$RC" -eq 0 ]; then
  echo "FIX OK: conan create passed with the compat shim (log: $LOG)"
  exit 0
fi
echo "FIX FAILED: conan create exit $RC; see $LOG" >&2
exit 1
