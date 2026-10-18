cmake_minimum_required(VERSION 3.15)
project(test_libthreadar LANGUAGES CXX)

find_package(libthreadar CONFIG REQUIRED)

add_executable(test_libthreadar test_package.cpp)
target_compile_features(test_libthreadar PRIVATE cxx_std_11)
target_link_libraries(test_libthreadar PRIVATE libthreadar::libthreadar)

enable_testing()
add_test(NAME test_libthreadar COMMAND test_libthreadar)
