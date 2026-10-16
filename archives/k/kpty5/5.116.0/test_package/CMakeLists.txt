cmake_minimum_required(VERSION 3.16)
project(test_kpty5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)
find_package(KF5Pty 5.116.0 REQUIRED)

add_executable(test_kpty5 test_kpty5.cpp)
target_link_libraries(test_kpty5 PRIVATE Qt5::Core KF5::Pty)

enable_testing()
add_test(NAME test_kpty5 COMMAND test_kpty5)
