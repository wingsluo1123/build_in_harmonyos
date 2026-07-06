cmake_minimum_required(VERSION 3.15)
project(test_btrfs-progs C)

# Find the package via Conan-generated CMakeDeps
find_package(btrfs-progs REQUIRED)

add_executable(test_btrfs-progs test.c)
target_link_libraries(test_btrfs-progs btrfs-progs::btrfs-progs)

enable_testing()
add_test(NAME test_btrfs-progs COMMAND test_btrfs-progs)
