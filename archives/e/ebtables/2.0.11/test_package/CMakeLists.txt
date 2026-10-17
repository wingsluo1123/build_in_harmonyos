cmake_minimum_required(VERSION 3.15)
project(test_package C)

# 交付的 CMake 契约（package_info 里 cmake_file_name = "ebtables"）
find_package(ebtables CONFIG REQUIRED)

add_executable(test_ebtables test_ebtables.c)
target_link_libraries(test_ebtables ebtables::ebtables)

enable_testing()
add_test(NAME test_ebtables COMMAND test_ebtables)
