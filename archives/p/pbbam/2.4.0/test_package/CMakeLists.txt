cmake_minimum_required(VERSION 3.15)
project(pbbam_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pbbam CONFIG REQUIRED)

add_executable(test_pbbam test_pbbam.cpp)
target_link_libraries(test_pbbam PRIVATE pbbam::pbbam)
