cmake_minimum_required(VERSION 3.15)
project(libosl_test_package CXX)

find_package(libosl CONFIG REQUIRED)

add_executable(test_osl test_osl.cpp)
target_link_libraries(test_osl PRIVATE libosl::libosl)
# Same standard as the library build (main recipe -std=c++14): Boost 1.84
# needs >=C++14, while upstream public headers predate C++17 removals, so a
# consumer compiling them at C++17 risks hard errors. Match the library.
target_compile_features(test_osl PRIVATE cxx_std_14)

enable_testing()
# One ctest case per CHECK group: deterministic discovery via `ctest -N`
# (Total Tests: 3) and per-case results in Testing/Temporary/LastTest.log.
add_test(NAME move_api COMMAND test_osl move_api)
add_test(NAME initial_state COMMAND test_osl initial_state)
add_test(NAME platform_config COMMAND test_osl platform_config)
