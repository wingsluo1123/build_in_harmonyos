cmake_minimum_required(VERSION 3.15)
project(test_profiled C)

# libprofile.h 公开暴露 <dbus/dbus.h>，消费方需要 dbus 头文件；glib 由 libprofile 运行期依赖
find_package(profiled CONFIG REQUIRED)
find_package(dbus CONFIG REQUIRED)
find_package(glib2 CONFIG REQUIRED)

add_executable(test_libprofile test_libprofile.c)
target_link_libraries(test_libprofile PRIVATE profiled::profiled dbus::dbus glib2::glib2)
