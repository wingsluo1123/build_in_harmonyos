cmake_minimum_required(VERSION 3.15)
project(test_gnu-typist C)

# Application package — no libraries to link; test via binary path
add_executable(test_gnu-typist test.c)
target_compile_definitions(test_gnu-typist PRIVATE
    GTYPIST_BINARY="$<TARGET_FILE:test_gnu-typist>")
# Gtypist binary path is passed via command-line argument in test.c

enable_testing()
add_test(NAME test_gnu-typist COMMAND test_gnu-typist)