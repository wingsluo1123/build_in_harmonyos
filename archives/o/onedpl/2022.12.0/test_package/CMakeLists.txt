cmake_minimum_required(VERSION 3.15)
project(test_onedpl CXX)

find_package(onedpl REQUIRED)

add_executable(test_onedpl test_onedpl.cpp)
target_link_libraries(test_onedpl PRIVATE onedpl::onedpl)
set_target_properties(test_onedpl PROPERTIES CXX_STANDARD 17 CXX_EXTENSIONS OFF)
