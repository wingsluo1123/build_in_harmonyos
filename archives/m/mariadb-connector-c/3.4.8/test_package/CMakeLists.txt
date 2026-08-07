cmake_minimum_required(VERSION 3.15)
project(test_mariadb_connector_c C)

# Find the package via Conan-generated CMakeDeps
find_package(mariadb-connector-c REQUIRED)

add_executable(test_mariadb_connector_c test.c)
target_link_libraries(test_mariadb_connector_c mariadb-connector-c::mariadb-connector-c)

enable_testing()
add_test(NAME test_mariadb_connector_c COMMAND test_mariadb_connector_c)
