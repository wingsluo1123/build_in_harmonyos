cmake_minimum_required(VERSION 3.15)
project(test_tntdb CXX)

find_package(tntdb CONFIG REQUIRED)
find_package(cxxtools CONFIG REQUIRED)

add_executable(test_tntdb test_tntdb.cpp)
# tntdb public headers (tntdb/bits/connection.h) include
# <cxxtools/smartptr.h>; link cxxtools explicitly so its include dirs
# are present even if transitive propagation through tntdb::tntdb is
# unavailable in the consumer toolchain context.
target_link_libraries(test_tntdb PRIVATE tntdb::tntdb cxxtools::cxxtools)

enable_testing()
add_test(NAME test_tntdb COMMAND test_tntdb)
