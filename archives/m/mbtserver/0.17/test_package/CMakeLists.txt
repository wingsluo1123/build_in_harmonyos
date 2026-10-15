cmake_minimum_required(VERSION 3.15)
project(test_mbtserver CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(mbtserver REQUIRED)
# Packaged public headers (vendored timbl/ticcutils trees) directly include
# unicode/unistr.h, libxml headers, zlib.h, bzlib.h. CMakeDeps does not
# expand transitive includes for consumers (dwarves/1.30 precedent), so each
# remote dep is found and linked explicitly.
find_package(icu REQUIRED)
find_package(libxml2 REQUIRED)
# zlib/bzip2 CMake target spelling varies by environment (vcflib precedent:
# official CI yields zlib::zlib/bzip2::bzip2, preflight may yield
# ZLIB::ZLIB/BZip2::BZip2), so probe both spellings.
find_package(zlib QUIET CONFIG)
if(NOT TARGET zlib::zlib)
  find_package(ZLIB QUIET)
endif()
find_package(bzip2 QUIET CONFIG)
if(NOT TARGET bzip2::bzip2)
  find_package(BZip2 QUIET)
endif()

add_executable(test_mbtserver test_mbtserver.cxx)
target_link_libraries(test_mbtserver PRIVATE mbtserver::mbtserver)
target_link_libraries(test_mbtserver PRIVATE icu::icu)
# libxml2's Conan recipe declares the CMake target LibXml2::LibXml2
# (upstream FindLibXml2 naming), not libxml2::libxml2 (libonvif precedent).
target_link_libraries(test_mbtserver PRIVATE LibXml2::LibXml2)
if(TARGET zlib::zlib)
  target_link_libraries(test_mbtserver PRIVATE zlib::zlib)
elseif(TARGET ZLIB::ZLIB)
  target_link_libraries(test_mbtserver PRIVATE ZLIB::ZLIB)
else()
  message(FATAL_ERROR "test_mbtserver: zlib CMake target not found (tried zlib::zlib, ZLIB::ZLIB)")
endif()
if(TARGET bzip2::bzip2)
  target_link_libraries(test_mbtserver PRIVATE bzip2::bzip2)
elseif(TARGET BZip2::BZip2)
  target_link_libraries(test_mbtserver PRIVATE BZip2::BZip2)
else()
  message(FATAL_ERROR "test_mbtserver: bzip2 CMake target not found (tried bzip2::bzip2, BZip2::BZip2)")
endif()
# The published libxml2 binary nests headers under <pkg>/include/libxml2/
# (libonvif precedent); cover the config-suffixed package-folder variable.
if(DEFINED libxml2_PACKAGE_FOLDER_RELEASE)
  target_include_directories(test_mbtserver PRIVATE "${libxml2_PACKAGE_FOLDER_RELEASE}/include/libxml2")
elseif(DEFINED libxml2_PACKAGE_FOLDER)
  target_include_directories(test_mbtserver PRIVATE "${libxml2_PACKAGE_FOLDER}/include/libxml2")
endif()

enable_testing()
add_test(NAME test_mbtserver COMMAND test_mbtserver)
