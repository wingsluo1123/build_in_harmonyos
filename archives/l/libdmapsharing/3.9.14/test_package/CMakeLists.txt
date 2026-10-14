cmake_minimum_required(VERSION 3.15)
project(test_dmapsharing C)

# libdmapsharing is STATIC and its public headers reference glib/gobject and
# <libsoup/soup.h>, and linking pulls the shared glib/soup/avahi/check
# runtimes. conan 2.29 CMakeDeps emits EMPTY data for transitive dependencies
# (libsoup3-r3 precedent), so the include dirs do NOT reach a consumer through
# the package's cpp_info.requires alone. The test_package therefore explicitly
# requires glib/libsoup3/avahi-glib/check and we find + link them here so the
# compiler gets the -I paths (libsoup-3.0, glib-2.0, ...) and the static
# libdmapsharing symbols resolve against the shared runtimes.
find_package(libdmapsharing-4.0 REQUIRED)
find_package(libsoup-3.0 REQUIRED)
find_package(GLib REQUIRED)
find_package(avahi-glib REQUIRED)
find_package(check REQUIRED)

add_executable(test_dmapsharing test_dmapsharing.c)
target_link_libraries(test_dmapsharing
    libdmapsharing-4.0::libdmapsharing-4.0
    libsoup-3.0::libsoup-3.0
    GLib::GLib
    GLib::GObject
    avahi-glib::avahi-glib
    Check::check)

enable_testing()
add_test(NAME test_dmapsharing COMMAND test_dmapsharing)
