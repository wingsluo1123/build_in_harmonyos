cmake_minimum_required(VERSION 3.16)
project(test_kcrash CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6CrashTargets.cmake references
find_package(Qt6 COMPONENTS Core REQUIRED)

find_package(KF6Crash REQUIRED NO_MODULE)

add_executable(test_kcrash test_kcrash.cpp)
target_link_libraries(test_kcrash KF6::Crash)

enable_testing()
add_test(NAME test_kcrash COMMAND test_kcrash)
