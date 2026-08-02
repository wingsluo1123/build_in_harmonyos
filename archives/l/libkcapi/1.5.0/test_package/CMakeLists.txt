cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via the Conan-generated CMakeDeps files.
find_package(libkcapi REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libkcapi::libkcapi)

enable_testing()

# TEST_LAUNCHER is set by test_package/conanfile.py from $CONFIG_SHELL.
# On HarmonyOS the default /system/bin/sh (mksh) refuses to exec the ELF
# directly, so the test is launched through the configured shell.  Everywhere
# else the variable is empty and the binary runs directly.
if(TEST_LAUNCHER)
  add_test(NAME test_package
           COMMAND "${TEST_LAUNCHER}" -c "$<TARGET_FILE:test_package>")
else()
  add_test(NAME test_package COMMAND test_package)
endif()
