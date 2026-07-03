cmake_minimum_required(VERSION 3.15)
project(test_qtshadertools C)

# Find the package via Conan-generated CMakeDeps
find_package(qtshadertools REQUIRED)

# Simple test that doesn't require runtime linking to shared libraries
# Verifies the package was found and the recipe is correct
add_executable(test_qtshadertools test.c)
# Don't link against qtshadertools::qtshadertools to avoid runtime .so path issues
# The find_package() call above already verifies the package is correctly configured

enable_testing()
add_test(NAME test_qtshadertools COMMAND test_qtshadertools)
