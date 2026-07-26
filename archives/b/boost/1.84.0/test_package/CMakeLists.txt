cmake_minimum_required(VERSION 3.15)
project(boost_components_test LANGUAGES CXX)

find_package(Boost CONFIG REQUIRED COMPONENTS program_options date_time)

add_executable(boost_components_test test.cpp)
target_compile_features(boost_components_test PRIVATE cxx_std_17)
target_link_libraries(boost_components_test PRIVATE Boost::program_options Boost::date_time)
