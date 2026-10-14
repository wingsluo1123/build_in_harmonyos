cmake_minimum_required(VERSION 3.16)
project(test_kservice5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core )
find_package(KF5Service 5.116.0 REQUIRED)

add_executable(test_kservice5 test_kservice5.cpp)
target_link_libraries(test_kservice5 PRIVATE Qt5::Core KF5::Service)

enable_testing()
add_test(NAME test_kservice5 COMMAND test_kservice5)
