cmake_minimum_required(VERSION 3.15)
project(test_libfiu C)

# Find the package via Conan-generated CMakeDeps
find_package(libfiu REQUIRED)

# Consumer must enable the fault-injection API, exactly like upstream
# tests do with -DFIU_ENABLE=1 (tests/Makefile ALL_CFLAGS). Without it
# fiu.h degrades fiu_init/fiu_fail/fiu_failinfo to no-op stubs and the
# consumer binaries prove nothing (hollow-pass risk).
add_compile_definitions(FIU_ENABLE=1)

add_executable(test_core test_core.c)
target_link_libraries(test_core libfiu::libfiu)

add_executable(test_control test_control.c)
target_link_libraries(test_control libfiu::libfiu)

enable_testing()
add_test(NAME test_core COMMAND test_core)
add_test(NAME test_control COMMAND test_control)
