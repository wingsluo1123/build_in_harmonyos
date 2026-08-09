cmake_minimum_required(VERSION 3.16)
project(test_adql LANGUAGES CXX)

find_package(adql REQUIRED)

add_executable(test_adql test_adql.cpp)
target_compile_features(test_adql PRIVATE cxx_std_17)
target_link_libraries(test_adql PRIVATE adql::adql)
