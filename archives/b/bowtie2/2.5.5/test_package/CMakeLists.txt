cmake_minimum_required(VERSION 3.15)
project(test_bowtie2 C)

# Find the package via Conan-generated CMakeDeps
find_package(bowtie2 REQUIRED)

add_executable(test_bowtie2 test.c)
target_link_libraries(test_bowtie2 bowtie2::bowtie2)

enable_testing()
add_test(NAME test_bowtie2 COMMAND test_bowtie2)
