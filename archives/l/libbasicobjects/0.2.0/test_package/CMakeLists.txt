cmake_minimum_required(VERSION 3.15)
project(libbasicobjects_probe C)

find_package(libbasicobjects REQUIRED)

add_executable(basicobjects_probe test.c)
target_link_libraries(basicobjects_probe PRIVATE libbasicobjects::libbasicobjects)

# 消费者阶段复跑上游官方单测(vendored 测试源,链接安装后的库)
add_executable(simplebuffer_ut upstream-test/simplebuffer_ut.c)
target_include_directories(simplebuffer_ut PRIVATE upstream-test)
target_link_libraries(simplebuffer_ut PRIVATE libbasicobjects::libbasicobjects)
