# CMakeLists.txt — pa-applet g20181009
#
# 上游只有 autotools（configure.ac + Makefile.am + autogen.sh），git 快照不含
# 预生成的 configure；构建环境没有 automake/aclocal，autogen.sh 直接失败：
#   Error: aclocal is required to run ./autogen.sh
# 因此由配方自带本构建脚本，按上游 Makefile.am 的源文件集合与安装项复刻构建。

cmake_minimum_required(VERSION 3.15)
project(pa-applet LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(GTK REQUIRED)          # gtk/3.24.43 → GTK::GTK
find_package(pulseaudio REQUIRED)    # pulseaudio/17.0 组件
find_package(libnotify REQUIRED)     # libnotify/0.8.3.1

set(PA_APPLET_SOURCES
    src/audio_status.c
    src/key_grabber.c
    src/main.c
    src/notifications.c
    src/popup_menu.c
    src/pulse_glue.c
    src/tray_icon.c
    src/volume_scale.c
)

add_executable(pa-applet ${PA_APPLET_SOURCES})
target_compile_definitions(pa-applet PRIVATE _GNU_SOURCE)
target_compile_options(pa-applet PRIVATE -Wall)
target_link_libraries(pa-applet PRIVATE
    GTK::GTK
    pulseaudio::pulse
    pulseaudio::pulse-mainloop-glib
    libnotify::libnotify
)

install(TARGETS pa-applet RUNTIME DESTINATION bin)
install(FILES man/pa-applet.1 DESTINATION share/man/man1)
