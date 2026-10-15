cmake_minimum_required(VERSION 3.15)
project(test_dbus C)
find_package(dbus CONFIG REQUIRED)

# OHOS links need the libc++ runtime; the same settings apply to every
# executable here.
function(hos_link_ohos target)
    if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
        target_link_options(${target} PRIVATE -stdlib=libc++)
        if(DEFINED OHOS_CXX_RUNTIME_DIR)
            target_link_libraries(${target} PRIVATE
                "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
                "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
                "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
            )
        endif()
    endif()
endfunction()

# Consumer flow: one connection routed through the daemon back to itself.
add_executable(test_dbus test.c)
target_link_libraries(test_dbus PRIVATE dbus::dbus)
hos_link_ohos(test_dbus)

# HarmonyOS-specific multi-process integration test:
#   dbus_hos_multiproc  orchestrator (probes the sandbox dir, starts the
#                       packaged daemon on a pathname AF_UNIX socket, drives
#                       both other processes, checks cleanup)
#   dbus_hos_service    separate service process (own name, object, loop)
#   dbus_hos_client     separate client process (own connection)
add_executable(dbus_hos_service dbus_hos_service.c)
target_link_libraries(dbus_hos_service PRIVATE dbus::dbus)
hos_link_ohos(dbus_hos_service)

add_executable(dbus_hos_client dbus_hos_client.c)
target_link_libraries(dbus_hos_client PRIVATE dbus::dbus)
hos_link_ohos(dbus_hos_client)

add_executable(dbus_hos_multiproc dbus_hos_multiproc.c)
hos_link_ohos(dbus_hos_multiproc)

# Test-harness-only getpwuid/getpwuid_r shim (LD_PRELOAD for dbus-daemon on
# this image; see hos_nopw.c for the exact scope). Never installed.
add_library(hos_nopw SHARED hos_nopw.c)

enable_testing()
add_test(NAME test_dbus COMMAND $<TARGET_FILE:test_dbus>)
