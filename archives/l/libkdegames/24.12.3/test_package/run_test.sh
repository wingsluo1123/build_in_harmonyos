#!/bin/sh
# test_package runner for libkdegames 24.12.3 (OHOS).
#
# Why this wrapper exists:
# 1. ctest's ENVIRONMENT property replaces the whole test process
#    environment, dropping the conan-provided loader path.
# 2. Several published KF6 packages carry build-tree-relative DT_NEEDED
#    entries like "../../bin/libKF6ConfigCore.so". The OHOS musl loader
#    resolves those relative to the process cwd, so a flat "bin" dir two
#    levels up from the cwd must contain copies of the needed libraries.
#    LKG_TEST_RUN_CWD points at <build_folder>/loader-root/sub/sub, whose
#    "../../bin" is the mirror prepared by test_package/conanfile.py; the
#    wrapper repeats the preparation at run time as a belt-and-braces
#    fallback (the CI sandbox may deny some filesystem operations during
#    generate()).
#
# The wrapper prints diagnostics (cwd, mirror dir listing) so that CI
# failures are diagnosable from the conan create log, then execs the test
# binary so the exit code propagates.
set -euo pipefail

LKG_TEST_LIB_DIRS="${LKG_TEST_LIB_DIRS:-}"
LKG_TEST_RUN_CWD="${LKG_TEST_RUN_CWD:-}"
MIRROR_BASE="${LKG_TEST_RUN_CWD:+$LKG_TEST_RUN_CWD/../../bin}"
MIRROR_BASE="${MIRROR_BASE:-$(pwd)/../../bin}"

# Mirror every dependency library into the relative NEEDED resolution base
# and into <cwd>/bin. Copies, not symlinks: the CI sandbox denies symlink
# creation on HMDFS.
if [ -n "$LKG_TEST_LIB_DIRS" ]; then
    OLDIFS="$IFS"
    IFS=":"
    for base in "$MIRROR_BASE" "$(pwd)/bin"; do
        [ -d "$base" ] || mkdir -p "$base" 2>/dev/null || true
    done
    for dir in $LKG_TEST_LIB_DIRS; do
        [ -d "$dir" ] || continue
        for base in "$MIRROR_BASE" "$(pwd)/bin"; do
            for f in "$dir"/libKF6*.so* "$dir"/libKDEGames*.so* "$dir"/libQt6*.so*; do
                [ -f "$f" ] || continue
                name="${f##*/}"
                if [ ! -e "$base/$name" ]; then
                    cp -f "$f" "$base/$name" 2>/dev/null || true
                fi
            done
        done
    done
    IFS="$OLDIFS"

    LD_LIBRARY_PATH="$LKG_TEST_LIB_DIRS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export LD_LIBRARY_PATH
fi

QT_QPA_PLATFORM=offscreen
export QT_QPA_PLATFORM

# Resolve the test binary to an absolute path *before* changing cwd: conan
# invokes the wrapper with a relative "./test_libkdegames", which would no
# longer resolve after the cd below.
EXE="${1:-}"
shift 2>/dev/null || true
case "$EXE" in
    /*) ;;
    *) EXE="$(pwd)/${EXE#./}" ;;
esac

# Run from the prepared tree so that build-tree-relative DT_NEEDED entries
# ("../../bin/libKF6*.so") resolve inside the mirror, never inside the
# recipe sources.
if [ -n "$LKG_TEST_RUN_CWD" ]; then
    mkdir -p "$LKG_TEST_RUN_CWD" 2>/dev/null || true
    cd "$LKG_TEST_RUN_CWD"
fi

# Diagnostics (stdout goes into the conan create log / LastTest.log).
echo "[run_test.sh] cwd=$(pwd)"
echo "[run_test.sh] mirror=$MIRROR_BASE"
echo "[run_test.sh] mirror entries: $(ls "$MIRROR_BASE" 2>/dev/null | wc -l)"
ls "$MIRROR_BASE" 2>/dev/null | head -5 | sed 's/^/[run_test.sh]   /' || true

exec "$EXE" "$@"
