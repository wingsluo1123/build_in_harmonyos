# test_package/CMakeLists.txt — sokol 0.0-git.2e75443 consumer test
#
# Two TUs against the packaged headers:
#   - test_sokol.c   (C99)  : consumer-perspective API contract suite
#   - test_sokol.cc  (C++11): sokol_cmdbuf implementation section
#                             compiled as C++ (patch s0001 target)
#
# The sokol implementation sections are compiled in SOKOL_DUMMY_BACKEND
# mode inside the test binary (the canonical way to consume the headers
# in a headless/command-line environment; graphics backend binding is a
# per-consumer decision by upstream design).
cmake_minimum_required(VERSION 3.15)
project(test_sokol C CXX)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(sokol REQUIRED)

# C consumer TU: 11 headers exercised for real (setup/shutdown lifecycles,
# args parsing, time math, fetch real-file async load, color/shape math,
# letterbox viewport, memtrack alloc/free, log smoke, framebuffer)
add_executable(test_sokol_c test_sokol.c)
target_link_libraries(test_sokol_c PRIVATE sokol::sokol m)
target_compile_definitions(test_sokol_c PRIVATE SOKOL_DUMMY_BACKEND)

# C++ consumer TU: sokol_cmdbuf impl section compiled as C++ (the
# upstream compile-suite contract; exercises patch s0001). The C++
# runtime is linked statically so the test binary is self-contained —
# the conanrun environment does not provide libc++_shared.so (the C TU
# needs no C++ runtime and runs as-is).
add_executable(test_sokol_cxx test_sokol.cc)
target_link_libraries(test_sokol_cxx PRIVATE sokol::sokol m)
target_compile_definitions(test_sokol_cxx PRIVATE SOKOL_DUMMY_BACKEND)
target_link_options(test_sokol_cxx PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME test_sokol_c    COMMAND test_sokol_c)
add_test(NAME test_sokol_cxx COMMAND test_sokol_cxx)
