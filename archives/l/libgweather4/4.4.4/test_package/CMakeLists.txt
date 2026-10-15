cmake_minimum_required(VERSION 3.15)
project(test_libgweather4 C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=gweather-4).
find_package(gweather-4 CONFIG REQUIRED)
# OHPCD's glib/2.84.0.1 exports the find-package name "GLib" (its recipe sets
# cpp_info cmake_file_name=GLib), not upstream pkg-config's "glib-2.0".
find_package(GLib CONFIG REQUIRED)

add_executable(test_libgweather4 test_libgweather4.c)
target_link_libraries(test_libgweather4
    gweather-4::gweather-4
    GLib::GLib
    GLib::GObject
    m
)

add_executable(test_detect_degraded test_detect_degraded.c)
# Gio::Gio is needed for G_IO_ERROR_NOT_SUPPORTED / g_error_domain: the
# G_IO_ERROR_* codes live in libglib's GIO library, not libgweather's.
target_link_libraries(test_detect_degraded
    gweather-4::gweather-4
    GLib::GLib
    GLib::GObject
    GLib::Gio
)

enable_testing()
add_test(NAME test_libgweather4 COMMAND test_libgweather4)
add_test(NAME test_detect_degraded COMMAND test_detect_degraded)
