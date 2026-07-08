cmake_minimum_required(VERSION 3.15)
project(test_coturn C)

# Find coturn via Conan-generated CMakeDeps
find_package(coturn REQUIRED)

# Dependencies (openssl, libevent, sqlite3) are transitive through coturn's
# Conan requirements — CMakeDeps automatically resolves them.
add_executable(test_coturn test.c)
target_link_libraries(test_coturn coturn::coturn)

enable_testing()
add_test(NAME test_coturn COMMAND test_coturn)
