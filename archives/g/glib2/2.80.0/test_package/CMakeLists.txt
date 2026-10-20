cmake_minimum_required(VERSION 3.15)
project(test_glib2 C)

find_package(glib2 REQUIRED)

add_executable(test_glib2 test_glib.c)
target_link_libraries(test_glib2 PRIVATE glib2::glib2)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  add_executable(test_glib_harmonyos test_glib_harmonyos.c)
  target_link_libraries(test_glib_harmonyos PRIVATE glib2::glib2)
endif()

enable_testing()
add_test(NAME test_glib2 COMMAND test_glib2)
if(TARGET test_glib_harmonyos)
  add_test(NAME test_glib_harmonyos COMMAND test_glib_harmonyos)
endif()
