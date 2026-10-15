cmake_minimum_required(VERSION 3.15)
project(test_kea C CXX)

# find_package() proves the exported Conan target is usable: the C++ program
# below compiles against the packaged include/kea headers and links two of the
# packaged libraries.
find_package(kea REQUIRED)

# Consumer contract: drives the isc::Exception API from libkea-exceptions and
# isc::util::str from libkea-util, and compiles the boost-dependent public
# headers (dhcp/pkt.h, util/str.h), proving the transitive boost headers reach
# the consumer.
add_executable(test_kea_api test_kea_api.cpp)
target_link_libraries(test_kea_api PRIVATE kea::kea)
set_target_properties(test_kea_api PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

# HarmonyOS-specific test #1 (platform ABI): verifies the packaged kea-dhcp4
# daemon carries the OHOS aarch64 / musl / libc++ platform ABI signature and
# that the OHOS loader maps it with RTLD_NOW.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea::kea
    ${CMAKE_DL_LIBS})
set_target_properties(test_ohos_platform PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON)

# HarmonyOS-specific test #2 (runtime closure): every packaged Kea library and
# hook plug-in must resolve its complete NEEDED closure under the OHOS loader,
# and the hook contract symbols must be importable at run time.
add_executable(test_ohos_runtime test_ohos_runtime.c)
target_link_libraries(test_ohos_runtime PRIVATE
    kea::kea
    ${CMAKE_DL_LIBS})
set_target_properties(test_ohos_runtime PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON)
