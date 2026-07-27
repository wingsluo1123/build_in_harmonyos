cmake_minimum_required(VERSION 3.15)
project(test_qtpositioning LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt5
find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Core)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Core Positioning)

# Find the package via Conan-generated CMakeDeps
find_package(qtpositioning REQUIRED)

add_executable(test_qtpositioning test.cpp)
target_link_libraries(test_qtpositioning PRIVATE
    qtpositioning::qtpositioning
    Qt${QT_VERSION_MAJOR}::Core
)

enable_testing()
add_test(NAME test_qtpositioning COMMAND test_qtpositioning)
