cmake_minimum_required(VERSION 3.15)
project(test_hashlink C)

# hashlink's CMakeLists.txt declares cmake_minimum_required 3.1 which is
# rejected by cmake 4.x. Pass the policy floor for the consumer project too.
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)

# Find the package via Conan-generated CMakeDeps. The recipe sets
# pkg_config_name=hashlink and cpp_info.libs=["hl"], so the canonical
# CMake target is hashlink::hashlink (auto-generated from recipe `name`).
find_package(hashlink REQUIRED)

add_executable(test_hashlink test.c)
target_link_libraries(test_hashlink PRIVATE hashlink::hashlink)

enable_testing()
add_test(NAME test_hashlink COMMAND test_hashlink)