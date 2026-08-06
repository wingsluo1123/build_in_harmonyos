cmake_minimum_required(VERSION 3.15)
project(test_gnome_autoar C)

find_package(gnome-autoar REQUIRED)
find_package(GLib REQUIRED)
find_package(libarchive REQUIRED)

add_executable(test_gnome_autoar test.c)

# Workaround: OHOS-adapted Conan CMakeDeps doesn't populate
# component-level includedirs from glib/libarchive packages.
# Add include directories manually using package folder variables.
target_include_directories(test_gnome_autoar PRIVATE
    ${glib_PACKAGE_FOLDER_RELEASE}/include
    ${glib_PACKAGE_FOLDER_RELEASE}/include/glib-2.0
    ${glib_PACKAGE_FOLDER_RELEASE}/lib/glib-2.0/include
    ${libarchive_PACKAGE_FOLDER_RELEASE}/include
)

target_link_libraries(test_gnome_autoar
    gnome-autoar::gnome-autoar
    GLib::GLib
    GLib::GObject
    GLib::Gio
    LibArchive::LibArchive
)

enable_testing()
add_test(NAME test_gnome_autoar COMMAND test_gnome_autoar)
