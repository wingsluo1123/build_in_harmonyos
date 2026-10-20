cmake_minimum_required(VERSION 3.16)
project(test_qmf CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core DBus Sql Network Xml Core5Compat)
find_package(qmf REQUIRED)

add_executable(test_qmf test_qmf.cpp)
target_link_libraries(test_qmf PRIVATE Qt6::Core Qt6::DBus Qt6::Sql Qt6::Network Qt6::Xml Qt6::Core5Compat qmf::qmf)

enable_testing()
add_test(NAME test_qmf COMMAND test_qmf)
