cmake_minimum_required(VERSION 3.15)
project(test_graphene C)

find_package(graphene-1.0 REQUIRED CONFIG)

add_executable(test_graphene test_graphene.c)
target_link_libraries(test_graphene PRIVATE graphene-1.0::graphene-1.0)
