# test_package/CMakeLists.txt
# Minimal test to verify Blender headless build works

cmake_minimum_required(VERSION 3.10)
project(blender_test)

find_package(blender REQUIRED)

# Just check that blender executable exists and is executable
add_executable(blender_test main.cpp)

# The actual test will be running blender --version via conanrun
