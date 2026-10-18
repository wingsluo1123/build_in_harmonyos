cmake_minimum_required(VERSION 3.15)
project(toontag_consumer CXX)

find_package(toontag CONFIG REQUIRED)
find_package(toon CONFIG QUIET)

add_executable(test_toontag test_toontag.cpp)
target_link_libraries(test_toontag PRIVATE toontag::toontag)
# NEWCPPSTD is exported via toontag's cpp_info.defines; belt-and-braces for
# generators that do not propagate defines to plain consumers.
target_compile_definitions(test_toontag PRIVATE NEWCPPSTD)
target_compile_features(test_toontag PRIVATE cxx_std_17)
