cmake_minimum_required(VERSION 3.15)
project(test_libaccounts-qt CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(libaccounts-qt REQUIRED)

add_executable(test_libaccounts-qt test.cpp)
target_link_libraries(test_libaccounts-qt libaccounts-qt::libaccounts-qt)

# Include QtXml headers (not declared as separate component in qt5-qtbase conan recipe)
include(${CMAKE_BINARY_DIR}/generators/qtxml_include.cmake OPTIONAL)

enable_testing()
add_test(NAME test_libaccounts-qt COMMAND test_libaccounts-qt)
