cmake_minimum_required(VERSION 3.16)
project(test_kcmutils LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(KF6KCMUtils REQUIRED CONFIG)

# Consumer application: drives the KCM load / dialog / fallback workflow.
add_executable(test_kcmutils test_kcmutils.cpp)
target_link_libraries(test_kcmutils PRIVATE Qt6::Widgets KF6::KCMUtils KF6::KCMUtilsCore)

# KCM plugin built by the consumer itself (real plugin, loaded at runtime).
add_library(consumer_kcm MODULE consumer_kcm.cpp)
target_link_libraries(consumer_kcm PRIVATE Qt6::Widgets KF6::KCMUtils)
set_target_properties(consumer_kcm PROPERTIES PREFIX "")

enable_testing()
add_test(NAME test_kcmutils COMMAND test_kcmutils $<TARGET_FILE:consumer_kcm>)
