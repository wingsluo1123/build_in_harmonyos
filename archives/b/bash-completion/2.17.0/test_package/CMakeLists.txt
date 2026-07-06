cmake_minimum_required(VERSION 3.15)
project(test_bash-completion C)

# Find the package via Conan-generated CMakeDeps
find_package(bash-completion REQUIRED)

add_executable(test_bash-completion test.c)
target_link_libraries(test_bash-completion bash-completion::bash-completion)

enable_testing()
add_test(NAME test_bash-completion COMMAND test_bash-completion)
