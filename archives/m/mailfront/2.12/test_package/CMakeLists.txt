cmake_minimum_required(VERSION 3.16)
project(mailfront_test_package C)

find_package(mailfront CONFIG REQUIRED)
find_package(cvm CONFIG REQUIRED)
find_package(bglibs CONFIG REQUIRED)

add_executable(consumer consumer.c)
target_include_directories(consumer PRIVATE "${MAILFRONT_INCLUDE_DIR}")
target_link_libraries(consumer PRIVATE bglibs::bglibs)

add_executable(mailfront_testcvm auth_module.c)
target_link_libraries(mailfront_testcvm PRIVATE cvm::module bglibs::bglibs)
