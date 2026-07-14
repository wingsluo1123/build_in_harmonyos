cmake_minimum_required(VERSION 3.15)
project(test_sentry C)

find_package(sentry REQUIRED)

add_executable(test_sentry test_sentry.c)
target_link_libraries(test_sentry sentry::sentry)

enable_testing()
add_test(NAME test_sentry COMMAND test_sentry)
