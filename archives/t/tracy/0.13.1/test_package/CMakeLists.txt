cmake_minimum_required(VERSION 3.15)
project(test_tracy CXX)

# Conan 2 CMakeDeps generates targets as `<recipe_name>::<recipe_name>` (lowercased).
# Recipe name is `tracy` → the consumer target is `tracy::tracy`.
find_package(tracy REQUIRED)

add_executable(test_tracy test.cpp)
target_compile_definitions(test_tracy PRIVATE TRACY_ENABLE)
target_link_libraries(test_tracy PRIVATE tracy::tracy)

enable_testing()
add_test(NAME test_tracy COMMAND test_tracy)