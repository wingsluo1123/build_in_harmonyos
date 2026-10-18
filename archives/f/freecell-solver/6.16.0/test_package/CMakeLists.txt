cmake_minimum_required(VERSION 3.16)
project(test_freecell_solver LANGUAGES C)

# The package exports no upstream CMake config; CMakeDeps generates
# freecell-solver-config.cmake for the exported target.
find_package(freecell-solver CONFIG REQUIRED)

add_executable(test_freecell_solver test.c)
target_link_libraries(test_freecell_solver PRIVATE
    freecell-solver::freecell-solver)
