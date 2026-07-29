cmake_minimum_required(VERSION 3.15)
project(test_sfml LANGUAGES CXX)

find_package(SFML CONFIG REQUIRED COMPONENTS System Network)

add_executable(test_sfml test_sfml.cpp)
target_link_libraries(test_sfml PRIVATE SFML::System SFML::Network)
target_compile_features(test_sfml PRIVATE cxx_std_17)
