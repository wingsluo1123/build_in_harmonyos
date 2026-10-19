cmake_minimum_required(VERSION 3.15)
project(kmag_consumer_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)

add_executable(qimage_smoke qimage_smoke.cpp)
target_link_libraries(qimage_smoke PRIVATE Qt6::Gui Qt6::Core)
