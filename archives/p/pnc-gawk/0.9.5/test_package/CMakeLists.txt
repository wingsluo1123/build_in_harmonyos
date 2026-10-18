cmake_minimum_required(VERSION 3.12)
project(test_pnc_gawk C)

# HarmonyOS PC (OHOS) native test: CMakeToolchain maps the OHOS conan profile
# (os=OHOS) to CMAKE_SYSTEM_NAME=HarmonyOS; compile in the OHOS_TARGET marker
# on that platform only.
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE ${CMAKE_DL_LIBS})
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_compile_definitions(test_ohos PRIVATE OHOS_TARGET=1)
endif()
