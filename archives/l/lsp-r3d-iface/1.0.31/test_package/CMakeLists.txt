cmake_minimum_required(VERSION 3.15)
project(test_lsp-r3d-iface CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(lsp-r3d-iface REQUIRED)

add_executable(test_lsp-r3d-iface test.cpp)
target_link_libraries(test_lsp-r3d-iface PRIVATE lsp-r3d-iface::lsp-r3d-iface)

get_target_property(_INC lsp-r3d-iface::lsp-r3d-iface INTERFACE_INCLUDE_DIRECTORIES)
get_target_property(_LL  lsp-r3d-iface::lsp-r3d-iface INTERFACE_LINK_LIBRARIES)
message(STATUS "PROBE iface INC=${_INC}")
message(STATUS "PROBE iface LL =${_LL}")
if(TARGET lsp-common-lib::lsp-common-lib)
  get_target_property(_CINC lsp-common-lib::lsp-common-lib INTERFACE_INCLUDE_DIRECTORIES)
  get_target_property(_CLL  lsp-common-lib::lsp-common-lib INTERFACE_LINK_LIBRARIES)
  message(STATUS "PROBE common INC=${_CINC}")
  message(STATUS "PROBE common LL =${_CLL}")
else()
  message(STATUS "PROBE common target MISSING")
endif()
