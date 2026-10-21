cmake_minimum_required(VERSION 3.16)
project(test_karchive5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 CONFIG REQUIRED COMPONENTS Core)
find_package(KF5Archive 5.116.0 CONFIG REQUIRED)

add_executable(test_karchive5 test.cpp)
target_link_libraries(test_karchive5 PRIVATE Qt5::Core KF5::Archive)

enable_testing()
add_test(NAME test_karchive5 COMMAND test_karchive5)
