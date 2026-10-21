cmake_minimum_required(VERSION 3.16)
project(wvkbd_ime LANGUAGES C CXX)
# Pass the Conan CMakeDeps directory as wvkbd_DIR (or CMAKE_PREFIX_PATH).
# No fallback to sources or a host library: the HAP consumes the installed package.
if(NOT DEFINED wvkbd_DIR AND DEFINED ENV{WVKBD_CONAN_GENERATORS} AND
   NOT "$ENV{WVKBD_CONAN_GENERATORS}" STREQUAL "")
    set(wvkbd_DIR "$ENV{WVKBD_CONAN_GENERATORS}" CACHE PATH "Conan CMakeDeps directory")
endif()
find_package(wvkbd CONFIG REQUIRED NO_CMAKE_FIND_ROOT_PATH)
add_library(wvkbd_napi SHARED wvkbd_napi.cpp)
target_compile_features(wvkbd_napi PRIVATE cxx_std_17)
set_target_properties(wvkbd_napi PROPERTIES SKIP_BUILD_RPATH ON)
target_link_libraries(wvkbd_napi PRIVATE wvkbd::core libace_napi.z.so)
target_compile_options(wvkbd_napi PRIVATE -Wall -Wextra -Werror -Wno-unused-command-line-argument)
