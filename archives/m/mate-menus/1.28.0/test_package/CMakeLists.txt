cmake_minimum_required(VERSION 3.15)
project(test_mate_menus C)

# Find the package via Conan-generated PkgConfigDeps
find_package(PkgConfig REQUIRED)
pkg_check_modules(MATE_MENU REQUIRED IMPORTED_TARGET libmate-menu)

add_executable(test_mate_menus test.c)
target_link_libraries(test_mate_menus PkgConfig::MATE_MENU)

enable_testing()
add_test(NAME test_mate_menus COMMAND test_mate_menus)
