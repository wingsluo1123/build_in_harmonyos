cmake_minimum_required(VERSION 3.16)
project(test_kcoreaddons CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6CoreAddonsTargets.cmake references
find_package(Qt6 COMPONENTS Core REQUIRED)

find_package(KF6CoreAddons REQUIRED NO_MODULE)

add_executable(test_kcoreaddons test_kcoreaddons.cpp)
target_link_libraries(test_kcoreaddons KF6::CoreAddons)

enable_testing()
add_test(NAME test_kcoreaddons COMMAND test_kcoreaddons)
