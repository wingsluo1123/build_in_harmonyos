cmake_minimum_required(VERSION 3.15)
project(test_lasem C)

# Find the package via Conan-generated CMakeDeps. The dependency headers
# (cairo.h / glib-object.h) are pulled in by lasem's public headers,
# and lld requires the explicit libraries on the link line for every symbol
# the test references directly (cairo_* calls, g_object_unref, and
# g_type_check_instance_is_a from the LSM_IS_* type checks) — link them by
# name using the generator-provided lib directories. Same pattern as the
# verified same-family lasem-render/0.5.1 test_package.
find_package(lasem REQUIRED)
find_package(cairo REQUIRED)
find_package(harfbuzz REQUIRED)
find_package(glib REQUIRED)

add_executable(test_lasem test_lasem.c)
target_link_directories(test_lasem PRIVATE
    ${cairo_LIB_DIRS_RELEASE}
    ${glib_LIB_DIRS_RELEASE}
    ${harfbuzz_LIB_DIRS_RELEASE})
target_link_libraries(test_lasem
    lasem::lasem
    harfbuzz::harfbuzz
    cairo
    gobject-2.0
    glib-2.0)
