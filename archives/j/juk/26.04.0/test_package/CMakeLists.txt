cmake_minimum_required(VERSION 3.16)
project(test_juk CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Consumer-side check of the library chain juk links against (KF6 config layer).
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6Config REQUIRED)

add_executable(test_juk test.cpp)
target_link_libraries(test_juk Qt6::Core KF6::ConfigCore)

enable_testing()
add_test(NAME test_juk COMMAND test_juk)
