cmake_minimum_required(VERSION 3.15)
project(test_lgogdownloader CXX)

# Dummy CMakeLists to satisfy Conan test_package structure
# The actual test runs lgogdownloader --version/--help

add_custom_target(test_lgogdownloader ALL
    COMMAND echo "test placeholder: actual test runs lgogdownloader --version"
)
enable_testing()
add_test(NAME lgogdownloader_version COMMAND echo "version check done via conanfile.py test()")
