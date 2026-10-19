cmake_minimum_required (VERSION 3.15)
project (ayatana-indicator-printers-test C)

# GLib/GIO provides the D-Bus client used by the integration check below.
find_package (glib REQUIRED)

add_executable (ohos-dbus-check ohos-dbus-check.c)
target_link_libraries (ohos-dbus-check PRIVATE GLib::Gio)
