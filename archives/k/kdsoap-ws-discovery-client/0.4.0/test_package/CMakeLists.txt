cmake_minimum_required(VERSION 3.18)
project(kdsoap_ws_discovery_client_consumer LANGUAGES CXX)

include(CTest)

find_package(KDSoapWSDiscoveryClient 0.4.0 CONFIG REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Core Network)

if(DEFINED CMAKE_SYSTEM_NAME AND CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    message(FATAL_ERROR "The HarmonyOS Conan profile must use CMAKE_SYSTEM_NAME=Linux for native CMake platform modules")
endif()

add_executable(test_consumer_api test_consumer_api.cpp)
target_link_libraries(test_consumer_api PRIVATE KDSoap::WSDiscoveryClient Qt6::Core)
add_test(NAME installed_consumer_api COMMAND test_consumer_api)

add_executable(test_ohos_loopback_probe test_ohos_loopback_probe.cpp)
target_link_libraries(test_ohos_loopback_probe PRIVATE KDSoap::WSDiscoveryClient Qt6::Core Qt6::Network)
add_test(NAME harmonyos_loopback_probe_parse COMMAND test_ohos_loopback_probe)
