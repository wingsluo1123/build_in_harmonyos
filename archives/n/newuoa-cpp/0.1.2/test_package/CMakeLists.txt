cmake_minimum_required(VERSION 3.15)
project(test_newuoa C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(newuoa-cpp REQUIRED)

# Consumer case: plain C public interface (installed header + static lib)
add_executable(test_newuoa_c test.c)
target_link_libraries(test_newuoa_c newuoa::newuoa)

# HarmonyOS-specific case: C++ closure-const public interface
add_executable(test_newuoa_ohos test_ohos.cpp)
target_link_libraries(test_newuoa_ohos newuoa::newuoa)
set_target_properties(test_newuoa_ohos PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_newuoa_c COMMAND test_newuoa_c)
add_test(NAME test_newuoa_ohos COMMAND test_newuoa_ohos)
