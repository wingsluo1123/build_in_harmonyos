message(STATUS "Conan: Using CMakeDeps conandeps_legacy.cmake aggregator via include()")
message(STATUS "Conan: It is recommended to use explicit find_package() per dependency instead")

find_package(LibXslt)
find_package(LibXml2)

set(CONANDEPS_LEGACY  LibXslt::LibXslt  LibXml2::LibXml2 )