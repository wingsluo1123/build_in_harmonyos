cmake_minimum_required(VERSION 3.16)
project(test_libquotient CXX)

# The QuotientQt6 package config carries the Qt6Gui/Qt6Network/Qt6Keychain
# find_dependency chain and defines the bare QuotientQt6 target (upstream
# export has no NAMESPACE).
find_package(Qt6 REQUIRED COMPONENTS Core Gui Network)
find_package(QuotientQt6 REQUIRED CONFIG)

add_executable(test_libquotient test_libquotient.cpp)
target_link_libraries(test_libquotient PRIVATE QuotientQt6 Qt6::Core)

enable_testing()
add_test(NAME test_libquotient COMMAND test_libquotient)
