cmake_minimum_required(VERSION 3.15)
project(test_qca_qt5 CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(Qt5 CONFIG REQUIRED)
find_package(Qca-qt5 REQUIRED)

# qt5-qtbase 配方组件未声明 libs/includedirs（CMakeDeps 目标为空壳）——
# 用 CMakeDeps 暴露的包目录变量定位包内 libQt5Core.so
find_library(QT5CORE_LIB Qt5Core
    PATHS "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib" NO_DEFAULT_PATH)

add_executable(test_qca_qt5 test.cpp)
target_link_libraries(test_qca_qt5 PRIVATE qca-qt5 ${QT5CORE_LIB})
