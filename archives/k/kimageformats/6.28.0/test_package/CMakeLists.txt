cmake_minimum_required(VERSION 3.16)
project(test_kimageformats LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.9 REQUIRED COMPONENTS Core Gui)

# kimageformats is a plugin package: verify the QImageIOHandler plugins were
# installed into the package's plugins/imageformats folder. The package root
# is passed by the recipe through the KIMAGEFORMATS_ROOT toolchain variable.
if(NOT DEFINED KIMAGEFORMATS_ROOT)
    message(FATAL_ERROR "KIMAGEFORMATS_ROOT not set by the Conan toolchain")
endif()

set(_plugin_dir "${KIMAGEFORMATS_ROOT}/plugins/imageformats")

# Unconditional core plugins (no gate in the upstream build).
set(CORE_PLUGINS
    kimg_ani kimg_ff kimg_hdr kimg_iff kimg_pcx kimg_pfm kimg_pic
    kimg_psd kimg_pxr kimg_qoi kimg_ras kimg_rgb kimg_sct kimg_tga kimg_tim
    kimg_xcf)
foreach(plugin IN LISTS CORE_PLUGINS)
    if(NOT EXISTS "${_plugin_dir}/${plugin}.so")
        message(FATAL_ERROR "missing core image format plugin: ${_plugin_dir}/${plugin}.so")
    endif()
endforeach()

# Optional plugins follow the recipe options, passed down as
# KIMAGEFORMATS_EXPECT_* variables (ON/OFF) by the test_package recipe.
macro(kimg_expect_optional fmt opt)
    if(${opt})
        if(NOT EXISTS "${_plugin_dir}/kimg_${fmt}.so")
            message(FATAL_ERROR "missing optional image format plugin: ${_plugin_dir}/kimg_${fmt}.so")
        endif()
    endif()
endmacro()
kimg_expect_optional(dds KIMAGEFORMATS_EXPECT_DDS)
kimg_expect_optional(exr KIMAGEFORMATS_EXPECT_OPENEXR)
kimg_expect_optional(raw KIMAGEFORMATS_EXPECT_LIBRAW)
kimg_expect_optional(jp2 KIMAGEFORMATS_EXPECT_OPENJPEG)
kimg_expect_optional(avif KIMAGEFORMATS_EXPECT_LIBAVIF)

file(GLOB installed_plugins "${_plugin_dir}/kimg_*.so")
list(LENGTH installed_plugins plugin_count)
if(plugin_count LESS 16)
    message(FATAL_ERROR "expected at least 16 kimg_*.so plugins, found ${plugin_count} in ${_plugin_dir}")
endif()

# The consumer executor loads the plugins through Qt's plugin infrastructure
# (QCoreApplication::addLibraryPath on the package's plugins directory).
add_executable(test_kimageformats test_kimageformats.cpp)
target_link_libraries(test_kimageformats PRIVATE Qt6::Core Qt6::Gui)
target_compile_definitions(test_kimageformats PRIVATE
    KIF_PLUGIN_DIR="${KIMAGEFORMATS_ROOT}/plugins"
    KIF_EXPECT_DDS=$<BOOL:${KIMAGEFORMATS_EXPECT_DDS}>
    KIF_EXPECT_OPENEXR=$<BOOL:${KIMAGEFORMATS_EXPECT_OPENEXR}>
    KIF_EXPECT_LIBRAW=$<BOOL:${KIMAGEFORMATS_EXPECT_LIBRAW}>
    KIF_EXPECT_OPENJPEG=$<BOOL:${KIMAGEFORMATS_EXPECT_OPENJPEG}>
    KIF_EXPECT_LIBAVIF=$<BOOL:${KIMAGEFORMATS_EXPECT_LIBAVIF}>)
