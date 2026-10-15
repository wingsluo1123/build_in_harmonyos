cmake_minimum_required(VERSION 3.15)
project(test_fbset C)

# fbset ships no library — the test binary spawns the packaged executable,
# whose path test_package/conanfile.py passes as argv[1].  Nothing to link;
# testing is driven by Conan, not CTest (same pattern as other CLI tools).
add_executable(test_fbset test_fbset.c)
