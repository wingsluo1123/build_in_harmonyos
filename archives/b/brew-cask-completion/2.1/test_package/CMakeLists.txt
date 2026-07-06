cmake_minimum_required(VERSION 3.15)
project(test_brew-cask-completion C)

# Find the package via Conan-generated CMakeDeps
find_package(brew-cask-completion REQUIRED)

add_executable(test_brew-cask-completion test.c)
target_link_libraries(test_brew-cask-completion brew-cask-completion::brew-cask-completion)

enable_testing()
add_test(NAME test_brew-cask-completion COMMAND test_brew-cask-completion)
