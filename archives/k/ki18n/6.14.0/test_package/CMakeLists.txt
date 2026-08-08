cmake_minimum_required(VERSION 3.16)
project(test_ki18n CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6I18nTargets.cmake references
find_package(Qt6 COMPONENTS Core REQUIRED)

find_package(KF6I18n REQUIRED NO_MODULE)

add_executable(test_ki18n test_ki18n.cpp)
target_link_libraries(test_ki18n KF6::I18n)

enable_testing()
add_test(NAME test_ki18n COMMAND test_ki18n)
