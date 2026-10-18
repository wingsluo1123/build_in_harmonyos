cmake_minimum_required(VERSION 3.16)
project(test_baloo_widgets CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(${CMAKE_CURRENT_LIST_DIR}/conan_cmakedeps_paths.cmake OPTIONAL)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
# No KF6Config.cmake is published by these packages, so the framework is
# resolved through the component config this recipe installs.
find_package(KF6BalooWidgets REQUIRED)

add_executable(test_baloo_widgets test_baloo_widgets.cpp)
target_link_libraries(test_baloo_widgets PRIVATE KF6::BalooWidgets Qt6::Widgets)

enable_testing()
add_test(NAME test_baloo_widgets COMMAND test_baloo_widgets)
