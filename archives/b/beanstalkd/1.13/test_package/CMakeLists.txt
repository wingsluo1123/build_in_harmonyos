cmake_minimum_required(VERSION 3.15)
project(test_beanstalkd C)

# Find the package via Conan-generated CMakeDeps
find_package(beanstalkd REQUIRED)

add_executable(test_beanstalkd test.c)
target_link_libraries(test_beanstalkd beanstalkd::beanstalkd)

enable_testing()
add_test(NAME test_beanstalkd COMMAND test_beanstalkd)
