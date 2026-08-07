cmake_minimum_required(VERSION 3.15)
project(test_notmuch C)

find_package(notmuch REQUIRED)

add_executable(test_notmuch test.c)
target_link_libraries(test_notmuch notmuch::notmuch)

enable_testing()
add_test(NAME test_notmuch COMMAND test_notmuch)
