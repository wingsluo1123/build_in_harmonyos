cmake_minimum_required(VERSION 3.15)
project(test_siril C)

# siril is an application (package_type=application), not a library.
# CMakeDeps does not populate siril_BINDIR for application packages (no libs
# → empty BIN_DIRS). The siril bindir path is passed directly as a CMake cache
# variable by the test conanfile.py via cmake.configure(cli_args=...).
# We do NOT call find_package(siril) because that would load sirilTargets.cmake
# which references transitive dependency CMake targets (e.g. opencv::opencv)
# that may not resolve correctly in the test environment.
if(NOT DEFINED SIRIL_BINDIR)
    message(FATAL_ERROR "SIRIL_BINDIR cache variable must be set by the test conanfile.py")
endif()

# Add the test executable
add_executable(test_siril test.c)

# Pass the siril bindir as a compile definition so the test can find the binary
target_compile_definitions(test_siril PRIVATE SIRIL_BINDIR="${SIRIL_BINDIR}")

enable_testing()
add_test(NAME test_siril COMMAND test_siril)
