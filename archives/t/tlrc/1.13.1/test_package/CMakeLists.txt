cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# tlrc is a Rust application (cargo build), no C library to link.
# This CMakeLists.txt is a placeholder for Conan CMakeDeps/CMakeToolchain generators.
# Real test runs in test_package/conanfile.py test() method via self.run().

add_custom_target(test_package ALL
    COMMAND echo "tlrc test_package: see conanfile.py test() method"
)
