cmake_minimum_required(VERSION 3.15)
project(test_nettle C)

find_package(nettle REQUIRED)
find_package(gmp REQUIRED)

add_executable(test_nettle test_nettle.c)
if(DEFINED gmp_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_nettle PRIVATE "${gmp_PACKAGE_FOLDER_RELEASE}/include")
endif()
target_link_libraries(test_nettle PRIVATE nettle::nettle gmp::gmp)
