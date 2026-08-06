message(STATUS "Conan: Using CMakeDeps conandeps_legacy.cmake aggregator via include()")
message(STATUS "Conan: It is recommended to use explicit find_package() per dependency instead")

find_package(gstreamer)
find_package(glib2)

set(CONANDEPS_LEGACY  gstreamer::gstreamer  glib2::glib2 )