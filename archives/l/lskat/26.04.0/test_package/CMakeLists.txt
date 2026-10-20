cmake_minimum_required(VERSION 3.15)
project(test_lskat C)

# Consumer test for lskat 26.04.0 (R34 — must actually exercise the binary).
# The real test logic is in test.sh (POSIX sh, kblocks 26.04.0 pattern) which
# runs the shipped lskat binary with --version/--help/--author/--license and
# launches it once so the OHOS dynamic linker has to resolve the whole
# DT_NEEDED closure, plus the OHOS-specific .codesign / AArch64 gate.
#
# This CMakeLists.txt + test_lskat.c pair is kept for test_package structural
# completeness (the L0c gate requires a test source in test_package/) and for
# out-of-band manual smoke builds. It is intentionally NOT wired into test():
# the recipe declares only the VirtualRunEnv generator and has no
# build()/CMakeDeps(), because the verification value here is running the
# packaged application, not compiling a C stub (kblocks 26.04.0 precedent).

add_executable(test_lskat test_lskat.c)

enable_testing()
add_test(NAME test_lskat COMMAND test_lskat)
