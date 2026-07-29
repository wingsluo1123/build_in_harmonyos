cmake_minimum_required(VERSION 3.15)
project(test_cgal LANGUAGES CXX)

find_package(CGAL CONFIG REQUIRED)

add_executable(test_cgal test_cgal.cpp)
target_link_libraries(test_cgal PRIVATE CGAL::CGAL)
target_compile_features(test_cgal PRIVATE cxx_std_17)
