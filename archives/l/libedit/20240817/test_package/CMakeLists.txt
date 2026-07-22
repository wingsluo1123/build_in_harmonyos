cmake_minimum_required(VERSION 3.15)
project(test_libedit C)

# Find the package via Conan-generated CMakeDeps
find_package(libedit REQUIRED)

# Find system ncurses (libedit runtime dependency)
# Support NCURSES_ROOT hint for cross-build environments
find_library(NCURSES_LIB NAMES ncursesw ncurses
  HINTS "$ENV{NCURSES_ROOT}/lib" "$ENV{NCURSES_PREFIX}/lib")
if(NOT NCURSES_LIB)
  message(FATAL_ERROR "ncurses library not found. "
    "Set NCURSES_ROOT or NCURSES_PREFIX environment variable to the ncurses installation prefix.")
endif()

find_path(NCURSES_INCLUDE_DIR curses.h
  HINTS "$ENV{NCURSES_ROOT}/include" "$ENV{NCURSES_PREFIX}/include"
    "$ENV{NCURSES_INCLUDE}")
if(NOT NCURSES_INCLUDE_DIR)
  message(FATAL_ERROR "ncurses header (curses.h) not found. "
    "Set NCURSES_ROOT, NCURSES_PREFIX, or NCURSES_INCLUDE environment variable.")
endif()

add_executable(test_libedit test_libedit.c)
target_link_libraries(test_libedit libedit::libedit ${NCURSES_LIB})
target_include_directories(test_libedit PRIVATE ${NCURSES_INCLUDE_DIR})

enable_testing()
add_test(NAME test_libedit COMMAND test_libedit)