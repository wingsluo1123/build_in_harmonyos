cmake_minimum_required(VERSION 3.15)
project(test_libedit C)

# Find the package via Conan-generated CMakeDeps
find_package(libedit REQUIRED)
# Also find ncurses (system dep, not conan dep)
find_library(NCURSES_LIB ncursesw PATHS /storage/Users/currentUser/usr/local/lib NO_DEFAULT_PATH)
find_path(NCURSES_INCLUDE_DIR curses.h PATHS /storage/Users/currentUser/tmp/test-install-ncurses-6.4/include NO_DEFAULT_PATH)

add_executable(test_libedit test_libedit.c)
target_link_libraries(test_libedit libedit::libedit ${NCURSES_LIB})
target_include_directories(test_libedit PRIVATE ${NCURSES_INCLUDE_DIR})

enable_testing()
add_test(NAME test_libedit COMMAND test_libedit)
