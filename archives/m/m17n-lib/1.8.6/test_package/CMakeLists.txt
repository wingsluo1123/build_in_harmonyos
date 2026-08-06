cmake_minimum_required(VERSION 3.15)
project(test_m17n-lib C)

# Find the package via Conan-generated CMakeDeps
find_package(m17n-lib REQUIRED)

add_executable(test_m17n-lib test.c)

# Link against m17n-lib (all libs: m17n-core, m17n, m17n-flt, m17n-gui)
target_link_libraries(test_m17n-lib m17n-lib::m17n-lib)

enable_testing()
add_test(NAME test_m17n-lib COMMAND test_m17n-lib)
