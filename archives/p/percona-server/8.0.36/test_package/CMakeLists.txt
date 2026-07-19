cmake_minimum_required(VERSION 3.16)
project(test_percona_server LANGUAGES C)

find_package(OpenSSL REQUIRED)

add_executable(test_client test_client.c)
target_link_libraries(test_client PRIVATE percona-server::percona-server OpenSSL::SSL OpenSSL::Crypto)

enable_testing()
add_test(NAME test_client COMMAND test_client)

