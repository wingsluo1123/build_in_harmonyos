cmake_minimum_required(VERSION 3.16)
project(test_kcrash CXX)

# KF6CrashConfig.cmake does find_dependency(Qt6Core) and KF6CrashTargets.cmake
# references Qt6::Core / Qt6::Gui targets, so load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui)

# Brings in KF6CrashTargets.cmake, exactly like a downstream KDE application
# consuming the package.
find_package(KF6Crash REQUIRED)

add_executable(test_kcrash test_kcrash.cpp)
target_link_libraries(test_kcrash PRIVATE KF6::Crash Qt6::Core)

# Deliberately crashing helper executed by the two E2E cases.
add_executable(consumer_crasher consumer_crasher.cpp)
target_link_libraries(consumer_crasher PRIVATE KF6::Crash Qt6::Core)

enable_testing()
add_test(NAME test_kcrash COMMAND test_kcrash)
