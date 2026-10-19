cmake_minimum_required(VERSION 3.15)
project(test_usbguard CXX)

# protobuf/3.17.3's Conan package is exported with cmake_find_mode=none, so
# CMakeDeps does not generate a protobuf config of its own: the imported
# usbguard target refers to the Conan target names `protobuf::protobuf` (and
# protobuf's vendored config, installed by Conan, bakes in `zlib::zlib`),
# while the configs actually reachable for the consumer are CMakeDeps'
# `ZLIB::ZLIB` and protobuf's own `protobuf::libprotobuf`.  Resolve the two
# names before importing usbguard so its link interface is complete.
find_package(ZLIB CONFIG REQUIRED)
if(NOT TARGET zlib::zlib)
  add_library(zlib::zlib INTERFACE IMPORTED)
  target_link_libraries(zlib::zlib INTERFACE ZLIB::ZLIB)
endif()

find_package(protobuf CONFIG REQUIRED)
if(NOT TARGET protobuf::protobuf)
  add_library(protobuf::protobuf INTERFACE IMPORTED)
  target_link_libraries(protobuf::protobuf INTERFACE protobuf::libprotobuf)
endif()

find_package(usbguard REQUIRED CONFIG)

add_executable(test_usbguard test_usbguard.cpp)
target_compile_features(test_usbguard PRIVATE cxx_std_17)
target_link_libraries(test_usbguard PRIVATE usbguard::usbguard)
