cmake_minimum_required(VERSION 3.16)
project(test_kprison CXX)

find_package(KF6Prison CONFIG REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Gui)

add_executable(test_kprison test_kprison.cpp)
target_link_libraries(test_kprison PRIVATE KF6::Prison Qt6::Gui)

enable_testing()
add_test(NAME test_kprison COMMAND test_kprison)
