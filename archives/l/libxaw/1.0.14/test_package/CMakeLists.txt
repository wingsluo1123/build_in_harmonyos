cmake_minimum_required(VERSION 3.15)
project(libxaw_consumer C)

find_package(libxaw CONFIG REQUIRED)

add_executable(libxaw7_widget_set_contract xaw7_contract.c)
target_link_libraries(libxaw7_widget_set_contract PRIVATE libxaw::xaw7)

add_executable(libxaw6_widget_set_contract xaw6_contract.c)
target_link_libraries(libxaw6_widget_set_contract PRIVATE libxaw::xaw6)
target_compile_definitions(libxaw6_widget_set_contract PRIVATE OLDXAW)
