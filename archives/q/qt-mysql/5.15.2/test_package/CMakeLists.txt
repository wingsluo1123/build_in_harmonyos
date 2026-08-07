cmake_minimum_required(VERSION 3.15)
project(test_qt_mysql CXX)

find_package(qt5-qtbase REQUIRED)

# Find Qt5Sql from qt-mysql package
find_library(QT5SQL_LIB Qt5Sql PATHS ${CMAKE_PREFIX_PATH} PATH_SUFFIXES lib)

add_executable(test_qt_mysql src/main.cpp)
target_link_libraries(test_qt_mysql Qt5::Core ${QT5SQL_LIB})
