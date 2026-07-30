cmake_minimum_required(VERSION 3.16)
project(test_percona_server LANGUAGES C CXX)

find_package(percona-server REQUIRED CONFIG)
find_package(openssl REQUIRED CONFIG)
find_package(zlib REQUIRED CONFIG)

add_executable(test_client test_client.c)
set_target_properties(test_client PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_client PRIVATE percona-server::percona-server openssl::openssl zlib::zlib)

enable_testing()
add_test(NAME test_client COMMAND test_client)
