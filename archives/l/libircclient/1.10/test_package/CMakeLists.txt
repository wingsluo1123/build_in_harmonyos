cmake_minimum_required(VERSION 3.15)
project(libircclient_consumer C)

find_package(libircclient CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(libircclient_consumer test_package.c)
target_link_libraries(libircclient_consumer PRIVATE
                      libircclient::libircclient
                      Threads::Threads)
