cmake_minimum_required(VERSION 3.15)
project(test_sidplay-libs CXX)

# Find the package via Conan-generated CMakeDeps
find_package(sidplay-libs REQUIRED)

add_executable(test_sidplay-libs test.cpp)
target_link_libraries(test_sidplay-libs sidplay-libs::sidplay-libs)

enable_testing()
add_test(NAME test_sidplay-libs COMMAND test_sidplay-libs)
