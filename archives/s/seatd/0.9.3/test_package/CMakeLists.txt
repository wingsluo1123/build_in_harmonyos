cmake_minimum_required(VERSION 3.15)
project(test_seatd C)

# Find the package via the Conan-generated CMakeDeps files.
find_package(seatd REQUIRED)

add_executable(test_seatd test_package.c)
target_link_libraries(test_seatd PRIVATE seatd::seatd)

enable_testing()

# TEST_LAUNCHER is set by test_package/conanfile.py from $CONFIG_SHELL.
# On HarmonyOS the default /system/bin/sh (mksh) refuses to exec the ELF
# directly, so the test is launched through the configured shell.  Everywhere
# else the variable is empty and the binary runs directly.
if(TEST_LAUNCHER)
  add_test(NAME test_seatd
           COMMAND "${TEST_LAUNCHER}" -c "$<TARGET_FILE:test_seatd>")
else()
  add_test(NAME test_seatd COMMAND test_seatd)
endif()
