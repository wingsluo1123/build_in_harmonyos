cmake_minimum_required(VERSION 3.15)
project(test_exiv2 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(exiv2 REQUIRED)

add_executable(test_exiv2 test.cpp)
target_link_libraries(test_exiv2 exiv2::exiv2)
target_compile_features(test_exiv2 PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_exiv2 COMMAND test_exiv2)
