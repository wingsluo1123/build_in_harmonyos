cmake_minimum_required(VERSION 3.16)
project(test_kdb LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The KDb CONFIG package (lib/cmake/KDb3/KDbConfig.cmake) pulls its own
# dependency chain: find_dependency(Qt5Core/Qt5Widgets/Qt5Xml 5.4.0 +
# KF5CoreAddons 5.16.0) plus the KDbTargets export that defines the plain
# `KDb` target.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)
find_package(KDb REQUIRED)

add_executable(test_kdb test.cpp)
target_link_libraries(test_kdb PRIVATE Qt5::Core KDb)
# $<TARGET_FILE:KDb> resolves the packaged libKDb3.so path through the
# imported target, so the R53 ELF assertions need no hardcoded prefix.
target_compile_definitions(test_kdb PRIVATE KDB_SO_PATH="$<TARGET_FILE:KDb>")

enable_testing()
add_test(NAME test_kdb COMMAND test_kdb)
