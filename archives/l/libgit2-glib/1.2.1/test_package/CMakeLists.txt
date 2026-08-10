cmake_minimum_required(VERSION 3.15)
project(test_libgit2_glib C)

find_package(libgit2-glib REQUIRED)
find_package(glib REQUIRED)
find_package(libgit2 REQUIRED)

add_executable(test_libgit2_glib test.c)
target_link_libraries(test_libgit2_glib libgit2-glib::libgit2-glib glib::glib libgit2::libgit2)
