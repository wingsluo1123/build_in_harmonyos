cmake_minimum_required(VERSION 3.15)
project(test_kscreenlocker CXX)

# The installed KScreenLockerConfig.cmake calls find_dependency(Qt6Core)
# and KScreenLockerTargets.cmake references Qt6::Core; the test itself
# additionally drives a QGuiApplication (Qt6::Gui), so load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KScreenLocker REQUIRED)

add_executable(test_kscreenlocker test_kscreenlocker.cpp)
target_link_libraries(test_kscreenlocker PW::KScreenLocker Qt6::Gui)

enable_testing()
add_test(NAME test_kscreenlocker COMMAND test_kscreenlocker)
