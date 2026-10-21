cmake_minimum_required(VERSION 3.15)
project(test_infnoise C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=libinfnoise)
find_package(libinfnoise REQUIRED)
# libinfnoise.h publicly includes <ftdi.h>; libftdi ships it in include/libftdi1
# (CMakeDeps exports it as LIBFTDI1_INCLUDE_DIRS_<CONFIG>)
find_package(libftdi1 REQUIRED)

# Consumer test (upper-layer component using the public API)
add_executable(test_infnoise test.c)
target_link_libraries(test_infnoise libinfnoise::libinfnoise)
# libinfnoise.h publicly includes <ftdi.h>; libftdi ships it in include/libftdi1
# (CMakeDeps defines the include root as libftdi1_INCLUDE_DIRS)
target_include_directories(test_infnoise PRIVATE ${libftdi1_INCLUDE_DIRS}/libftdi1)

# HarmonyOS special test (platform contract assertions, no-device)
add_executable(harmony_test harmony_test.c)
target_link_libraries(harmony_test libinfnoise::libinfnoise)
target_include_directories(harmony_test PRIVATE ${libftdi1_INCLUDE_DIRS}/libftdi1)

enable_testing()
add_test(NAME test_infnoise COMMAND test_infnoise)
add_test(NAME harmony_test COMMAND harmony_test)
