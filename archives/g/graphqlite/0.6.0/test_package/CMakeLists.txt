cmake_minimum_required(VERSION 3.15)
project(test_graphqlite C)

# Find the package via Conan-generated CMakeDeps
find_package(graphqlite REQUIRED)

add_executable(test_graphqlite test.c)
target_link_libraries(test_graphqlite graphqlite::graphqlite)

enable_testing()
add_test(NAME test_graphqlite COMMAND test_graphqlite)
