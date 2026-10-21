cmake_minimum_required(VERSION 3.15)
project(test_gupnp_dlna C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=
# gupnp-dlna-2.0). Only the package's own shared target is linked: its
# INTERFACE_LINK_LIBRARIES pull in glib2/libxml2/gstreamer/gst-plugins-base
# include dirs and archives, but the test references g_*/g_object_* and
# gupnp_dlna_* symbols that are exported by libgupnp-dlna-2.0.so, so the
# static glib archives are not extracted into the executable. Keeping one
# glib copy per process (anchored on the packaged .so) is deliberate: the
# OHOS ecosystem has static-only glib2/gstreamer and cross-DSO GType
# registry splits are a known failure mode (gst-plugins-bad1.0 notes).
find_package(gupnp-dlna-2.0 REQUIRED)

add_executable(test_gupnp_dlna test_gupnp_dlna.c)
target_link_libraries(test_gupnp_dlna PRIVATE
    gupnp-dlna-2.0::gupnp-dlna-2.0)

enable_testing()
add_test(NAME test_gupnp_dlna COMMAND test_gupnp_dlna)
