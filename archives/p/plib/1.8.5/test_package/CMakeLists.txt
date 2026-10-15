cmake_minimum_required(VERSION 3.5)
project(test_plib CXX)

find_package(plib REQUIRED CONFIG)

add_executable(test_plib test_plib.cc)
target_link_libraries(test_plib PRIVATE plib::plib)

enable_testing()
add_test(NAME plib_sg COMMAND test_plib)
