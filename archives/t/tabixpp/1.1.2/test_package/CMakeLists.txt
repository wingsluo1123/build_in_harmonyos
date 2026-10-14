cmake_minimum_required(VERSION 3.15)
project(test_tabixpp CXX)

find_package(tabixpp CONFIG REQUIRED)
find_package(htslib CONFIG REQUIRED)

add_executable(test_tabixpp test_tabixpp.cpp)
target_link_libraries(test_tabixpp PRIVATE tabixpp::tabixpp htslib::htslib)
target_compile_features(test_tabixpp PRIVATE cxx_std_17)
