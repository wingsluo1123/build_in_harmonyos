cmake_minimum_required(VERSION 3.16)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Consumer contract of this package (conan-generated, found through
# CMAKE_PREFIX_PATH): one target per delivered library.  Upstream's own
# per-component config files are delivered as files and are asserted by
# test_layout.py (they are the contract a non-conan consumer uses).
find_package(iceoryx CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package
    iceoryx::iceoryx_posh
    iceoryx::iceoryx_binding_c)
# Keep every linked iceoryx library in DT_NEEDED so that test_layout.py can
# verify the consumer really links all three delivered libraries (the consumer
# only *calls* into hoofs/binding_c directly).
target_link_options(test_package PRIVATE "-Wl,--no-as-needed")
