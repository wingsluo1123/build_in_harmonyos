cmake_minimum_required(VERSION 3.15)
project(test_apt-pkg CXX)

# C++17 is required by libapt-pkg public headers (apt-pkg 2.7.14)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(apt-pkg REQUIRED)

add_executable(test_apt-pkg test.cpp)
target_link_libraries(test_apt-pkg apt-pkg::apt-pkg)

enable_testing()
add_test(NAME test_apt-pkg COMMAND test_apt-pkg)
