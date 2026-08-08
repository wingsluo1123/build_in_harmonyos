cmake_minimum_required(VERSION 3.15)
project(test_apngasm CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# Find packages via Conan-generated CMakeDeps
find_package(apngasm REQUIRED)
find_package(PNG REQUIRED)
find_package(ZLIB REQUIRED)

add_executable(test_apngasm test_apngasm.cpp)
target_link_libraries(test_apngasm apngasm::apngasm PNG::PNG ZLIB::ZLIB)

enable_testing()
add_test(NAME test_apngasm COMMAND test_apngasm)
