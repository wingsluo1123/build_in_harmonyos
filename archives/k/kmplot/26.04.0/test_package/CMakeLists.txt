cmake_minimum_required(VERSION 3.15)
project(test_kmplot C)

# Consumer test for kmplot 26.04.0 (R34 — must actually exercise the binary).
# The real test logic is in test.sh (POSIX sh, kbreakout 26.04.0 pattern)
# which runs the shipped kmplot binary with --version/--help/--author and
# launches it once so the OHOS dynamic linker has to resolve the whole
# DT_NEEDED closure, then probes the kmplotpart KParts plugin module.
#
# This CMakeLists.txt + test_kmplot.c pair is kept for test_package
# structural completeness (the L0c gate requires a test source in
# test_package/) and for out-of-band manual smoke builds. It is intentionally
# NOT wired into test(): the recipe declares only the VirtualRunEnv generator
# and has no build()/CMakeDeps(), because the verification value here is
# running the packaged application, not compiling a C stub (kbreakout 26.04.0
# precedent).

add_executable(test_kmplot test_kmplot.c)

enable_testing()
add_test(NAME test_kmplot COMMAND test_kmplot)
