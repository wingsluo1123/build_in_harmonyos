cmake_minimum_required(VERSION 3.15)
project(test_qtpositioning LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt5 Core via Conan CMakeDeps (qt5-qtbase 定义组件 Qt5Core，
# 生成 Qt5CoreConfig.cmake 与 Qt5::Core target；无独立 Qt5Config.cmake)
find_package(Qt5Core REQUIRED)

# Find the package via Conan-generated CMakeDeps
find_package(qtpositioning REQUIRED)

add_executable(test_qtpositioning test.cpp)
target_link_libraries(test_qtpositioning PRIVATE
    Qt5::Positioning
    Qt5::Core
)

enable_testing()
add_test(NAME test_qtpositioning COMMAND test_qtpositioning)
