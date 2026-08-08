cmake_minimum_required(VERSION 3.16)
project(test_kconfig CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6ConfigTargets.cmake references
find_package(Qt6 COMPONENTS Core Xml REQUIRED)

find_package(KF6Config REQUIRED NO_MODULE)

add_executable(test_kconfig test_kconfig.cpp)
target_link_libraries(test_kconfig KF6::ConfigCore)

enable_testing()
add_test(NAME test_kconfig COMMAND test_kconfig)
