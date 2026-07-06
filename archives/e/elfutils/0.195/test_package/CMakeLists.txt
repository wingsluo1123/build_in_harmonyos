cmake_minimum_required(VERSION 3.15)
project(test_elfutils C)

# Use Conan-generated CMakeDeps targets
find_package(elfutils REQUIRED)

add_executable(test_elfutils test_elfutils.c)
target_link_libraries(test_elfutils PRIVATE elfutils::elfutils)
