cmake_minimum_required(VERSION 3.15)
project(paprefs_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTKMM REQUIRED IMPORTED_TARGET gtkmm-3.0)
pkg_check_modules(GIOMM REQUIRED IMPORTED_TARGET giomm-2.4)
pkg_check_modules(SIGC REQUIRED IMPORTED_TARGET sigc++-2.0)
pkg_check_modules(LIBPULSE REQUIRED IMPORTED_TARGET libpulse)

add_executable(test_paprefs test_paprefs.cpp)
target_link_libraries(test_paprefs
    PRIVATE
        PkgConfig::GTKMM
        PkgConfig::GIOMM
        PkgConfig::SIGC
        PkgConfig::LIBPULSE
)
