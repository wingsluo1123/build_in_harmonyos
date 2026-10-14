cmake_minimum_required(VERSION 3.16)
project(retro-gtk-consumer-test C)

set(CMAKE_C_STANDARD 11)

find_package(PkgConfig REQUIRED)

# 被测包（Conan PkgConfigDeps 生成的 .pc，路径指向包目录）
pkg_check_modules(RETRO_GTK REQUIRED IMPORTED_TARGET retro-gtk-1)
# 消费者自身还要用 GLib/GObject/GObject 断言（retro-gtk.h 只暴露自己的类型）
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0 gobject-2.0 gio-2.0)
pkg_check_modules(GDK_PIXBUF REQUIRED IMPORTED_TARGET gdk-pixbuf-2.0)

# 假 Libretro 核心：由消费者传给 RetroCore，retro-runner 会 dlopen 它
add_library(retro-test-core MODULE test_core.c)
target_link_libraries(retro-test-core PRIVATE PkgConfig::GLIB)

# 消费者：链接被测库，走 RetroCore 的公开 API
add_executable(retro-gtk-consumer consumer.c)
target_link_libraries(retro-gtk-consumer PRIVATE
    PkgConfig::RETRO_GTK
    PkgConfig::GLIB
    PkgConfig::GDK_PIXBUF
)
