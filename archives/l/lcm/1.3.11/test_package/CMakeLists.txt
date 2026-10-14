cmake_minimum_required(VERSION 3.15)
project(lcm_test LANGUAGES C)

# Find the installed lcm package (CMakeDeps generates lcm-config.cmake and the
# lcm::lcm target). lcm::lcm publicly requires glib::glib-2.0 / glib::gthread-2.0
# (see main recipe package_info), so CMakeDeps wires in the whole glib closure
# transitively — the consumer only links the lcm target.
find_package(lcm REQUIRED)

add_executable(test_lcm test_lcm.c)
target_link_libraries(test_lcm PRIVATE lcm::lcm)
