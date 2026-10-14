cmake_minimum_required(VERSION 3.15)
project(test_id3lib CXX)

# Package discovered via Conan-generated CMakeDeps config
find_package(id3lib REQUIRED)

add_executable(test_id3lib test.cpp)
target_link_libraries(test_id3lib id3lib::id3lib)

enable_testing()
add_test(NAME test_id3lib COMMAND test_id3lib)
