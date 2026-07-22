cmake_minimum_required(VERSION 3.15)
project(test_sdl3 C)

# R34: a real consumer exercising the public SDL3 API on OHOS.

find_package(SDL3 REQUIRED CONFIG)

add_executable(test_sdl3 test.c)
# SDL3's SDL_platform_defines.h defines SDL_PLATFORM_OHOS only when
# __OHOS__ is set. Our patches inject that into SDL3's own targets, but
# consumers must define it themselves for the public headers.
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OpenHarmony")
    target_compile_definitions(test_sdl3 PRIVATE __OHOS__=1)
endif()
target_link_libraries(test_sdl3 PRIVATE SDL3::SDL3)

# SDL3 uses the C math library (sin/cos in SDL_sqrt.c etc.) — link
# explicitly so the test binary doesn't fail at link time on bionic.
if(NOT WIN32)
    target_link_libraries(test_sdl3 PRIVATE m)
endif()

enable_testing()
add_test(NAME test_sdl3 COMMAND test_sdl3)