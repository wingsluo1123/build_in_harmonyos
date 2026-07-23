cmake_minimum_required(VERSION 3.15)
project(test_harfbuzz CXX)

# Find the package via Conan-generated CMakeDeps
find_package(harfbuzz REQUIRED)

add_executable(test_harfbuzz test.cpp)

# Link against harfbuzz (which transitively links graphite2 and freetype)
target_link_libraries(test_harfbuzz harfbuzz::harfbuzz)

enable_testing()
add_test(NAME test_harfbuzz COMMAND test_harfbuzz)
