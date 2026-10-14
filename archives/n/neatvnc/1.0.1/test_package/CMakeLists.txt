cmake_minimum_required(VERSION 3.15)
project(test_neatvnc C)
find_package(neatvnc CONFIG REQUIRED)
find_package(aml CONFIG REQUIRED)
add_executable(test_neatvnc test_neatvnc.c)
target_link_libraries(test_neatvnc PRIVATE neatvnc::neatvnc aml::aml)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  if(NOT neatvnc_LIB_DIRS_RELEASE OR NOT pixman_LIB_DIRS_RELEASE)
    message(FATAL_ERROR "Conan runtime library directories are unavailable")
  endif()
  target_link_options(test_neatvnc PRIVATE
    "-Wl,--disable-new-dtags"
    "-Wl,-rpath,${neatvnc_LIB_DIRS_RELEASE}:${pixman_LIB_DIRS_RELEASE}")
endif()
