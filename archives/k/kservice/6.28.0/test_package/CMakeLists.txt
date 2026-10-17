cmake_minimum_required(VERSION 3.16)
project(test_kservice LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# KF6ServiceConfig.cmake does find_dependency(Qt6 ...) for Core/Xml and the
# KF6Config/KF6CoreAddons/KF6I18n packages, so Qt6 must resolve first.
find_package(Qt6 6.9.0 REQUIRED COMPONENTS Core Xml)
find_package(KF6Service 6.28.0 REQUIRED)

add_executable(test_kservice test.cpp)
target_link_libraries(test_kservice PRIVATE Qt6::Core Qt6::Xml KF6::Service)

enable_testing()
add_test(NAME test_kservice COMMAND test_kservice)
