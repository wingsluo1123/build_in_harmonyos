cmake_minimum_required(VERSION 3.15)
project(test_krb5server C)

find_package(krb5-server CONFIG REQUIRED)

add_executable(test_krb5server test_krb5server.c)
target_link_libraries(test_krb5server PRIVATE krb5-server::krb5-server)
