cmake_minimum_required(VERSION 3.15)
project(test_xgboost C)

# Find the package via Conan-generated CMakeDeps
find_package(xgboost REQUIRED)

add_executable(test_xgboost test.c)
target_link_libraries(test_xgboost xgboost::xgboost)

enable_testing()
add_test(NAME test_xgboost COMMAND test_xgboost)
