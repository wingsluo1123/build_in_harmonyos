cmake_minimum_required(VERSION 3.15)
project(test_zinnia CXX)

# Find the package via Conan-generated CMakeDeps
find_package(zinnia REQUIRED)

add_executable(test_zinnia test_zinnia.cpp)
target_link_libraries(test_zinnia zinnia::zinnia)

# End-to-end HarmonyOS-specific consumer test (rule12): train -> model -> recognize
add_executable(test_zinnia_e2e test_zinnia_e2e.cpp)
target_link_libraries(test_zinnia_e2e zinnia::zinnia)

enable_testing()
add_test(NAME test_zinnia COMMAND test_zinnia)
add_test(NAME test_zinnia_e2e COMMAND test_zinnia_e2e)
