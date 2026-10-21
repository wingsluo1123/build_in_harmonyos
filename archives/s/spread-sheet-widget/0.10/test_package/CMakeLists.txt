cmake_minimum_required(VERSION 3.15)
project(test_spread_sheet_widget C)

# The installed spread-sheet-widget.pc carries
#   Requires: gtk+-3.0 >= 3.18.0 glib-2.0 >= 2.44
# so resolving this one module also proves the whole public dependency chain
# written at configure time is consumable.
find_package(PkgConfig REQUIRED)
pkg_check_modules(SPREADSHEETWIDGET REQUIRED IMPORTED_TARGET spread-sheet-widget)

add_executable(test_spread_sheet_widget test_spread_sheet_widget.c)
target_link_libraries(test_spread_sheet_widget PRIVATE
    PkgConfig::SPREADSHEETWIDGET)
