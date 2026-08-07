cmake_minimum_required(VERSION 3.15)
project(test_siril C)

# Find the package via Conan-generated CMakeDeps
find_package(siril REQUIRED)

# Add the test executable
add_executable(test_siril test.c)

# Pass the siril bindir as a compile definition so the test can find the binary
target_compile_definitions(test_siril PRIVATE SIRIL_BINDIR="${siril_BINDIR}")

# Link against siril package (for dependency resolution)
target_link_libraries(test_siril siril::siril)

enable_testing()
add_test(NAME test_siril COMMAND test_siril)
