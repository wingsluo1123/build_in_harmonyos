cmake_minimum_required(VERSION 3.15)
project(test_kcolorchooser C)

# Consumer test for kcolorchooser 26.04.0 (R34 — must actually exercise the
# shipped binary). The real verification logic lives in test.sh (POSIX sh,
# kblocks 26.04.0 pattern) and is driven from test_package/conanfile.py
# test(): it runs the packaged bin/kcolorchooser with --version/--help/
# --author/--license plus a HarmonyOS-specific library-closure load case.
# This CMakeLists.txt is structural only: it keeps a CMake-visible test target
# and a test source file in test_package/ (framework L0 structure gate).
# test_package/conanfile.py declares no build() and uses the VirtualRunEnv
# generator only, so this target is deliberately NOT configured, compiled or
# run during `conan create`; the actual verification is executed by test.sh
# from test_package/conanfile.py::test() (kblocks 26.04.0 precedent).

add_executable(test_kcolorchooser test_kcolorchooser.c)

enable_testing()
add_test(NAME test_kcolorchooser COMMAND test_kcolorchooser)
