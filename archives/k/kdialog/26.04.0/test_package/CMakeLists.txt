cmake_minimum_required(VERSION 3.15)
project(test_kdialog C)

# Consumer test for kdialog 26.04.0 (R34 — must actually exercise the shipped
# binaries). The real verification logic lives in test.sh (POSIX sh,
# kcolorchooser 26.04.0 pattern) and is driven from test_package/conanfile.py
# test(): it runs the packaged bin/kdialog with --version/--help/--author/
# --license, checks the unknown-option failure path, then probes the --msgbox
# modal event loop (alive-bounded) and the kdialog_progress_helper DT_NEEDED
# closure directly (both HarmonyOS-specific cases).
# This CMakeLists.txt is structural only: it keeps a CMake-visible test target
# and a test source file in test_package/ (framework L0 structure gate).
# test_package/conanfile.py declares no build() and uses the VirtualRunEnv
# generator only, so this target is deliberately NOT configured, compiled or
# run during `conan create`; the actual verification is executed by test.sh
# from test_package/conanfile.py::test() (kcolorchooser 26.04.0 precedent).

add_executable(test_kdialog test_kdialog.c)

enable_testing()
add_test(NAME test_kdialog COMMAND test_kdialog)
