cmake_minimum_required(VERSION 3.15)
project(test_plast CXX)

# plast-config.cmake comes from the Conan CMakeDeps generator and exposes the
# plast::plast target built from the recipe's cpp_info.
find_package(plast REQUIRED CONFIG)

add_executable(test_plast_api test_plast_api.cpp)
target_link_libraries(test_plast_api PRIVATE plast::plast)
