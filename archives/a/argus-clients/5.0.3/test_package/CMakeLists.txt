cmake_minimum_required(VERSION 3.15)
project(test_argus_clients C)

# Build a simple test program that links against argus static library
find_package(argus-clients REQUIRED)

add_executable(test_argus_clients test.c)
target_link_libraries(test_argus_clients argus-clients::argus-clients)

enable_testing()
add_test(NAME test_argus_clients COMMAND test_argus_clients)
