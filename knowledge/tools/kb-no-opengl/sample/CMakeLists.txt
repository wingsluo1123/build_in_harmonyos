cmake_minimum_required(VERSION 3.20)
project(qt6_noopengl_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 只需 Core/Gui：QOpenGLContext 在无 OpenGL 的 Qt6 构建里仍可从 QtGui 转发头 include，
# 这正是坑的形态（include 成功、符号不声明）。
find_package(Qt6 REQUIRED COMPONENTS Core Gui)

add_library(noopengldemo STATIC src/renderer.cpp)
target_include_directories(noopengldemo PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
target_link_libraries(noopengldemo PUBLIC Qt6::Core Qt6::Gui)
set_target_properties(noopengldemo PROPERTIES POSITION_INDEPENDENT_CODE ON)

install(TARGETS noopengldemo ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)
