# CMakeLists.txt for libtheora 1.1.1
# Created for OpenHarmony cross-compilation
# Replaces autotools build system with CMake
# Uses Conan CMakeDeps for libogg dependency

cmake_minimum_required(VERSION 3.10)
project(theora VERSION 1.1.1 LANGUAGES C)

# Set default build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Find libogg dependency (provided by Conan CMakeDeps)
find_package(Ogg REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Source files for theora decoder library
set(THEORA_DEC_SOURCES
    lib/analyze.c
    lib/apiwrapper.c
    lib/bitpack.c
    lib/decapiwrapper.c
    lib/decinfo.c
    lib/decode.c
    lib/dequant.c
    lib/fragment.c
    lib/huffdec.c
    lib/idct.c
    lib/info.c
    lib/internal.c
    lib/mathops.c
    lib/quant.c
    lib/state.c
)

# Source files for theora encoder library
set(THEORA_ENC_SOURCES
    lib/analyze.c
    lib/apiwrapper.c
    lib/bitpack.c
    lib/encapiwrapper.c
    lib/encfrag.c
    lib/encinfo.c
    lib/encode.c
    lib/enquant.c
    lib/fdct.c
    lib/fragment.c
    lib/huffenc.c
    lib/idct.c
    lib/internal.c
    lib/mathops.c
    lib/mcenc.c
    lib/quant.c
    lib/rate.c
    lib/state.c
    lib/tokenize.c
)

# Build static libraries
add_library(theoradec STATIC ${THEORA_DEC_SOURCES})
target_link_libraries(theoradec Ogg::ogg)
target_compile_options(theoradec PRIVATE -O2 -fPIC)

add_library(theoraenc STATIC ${THEORA_ENC_SOURCES})
target_link_libraries(theoraenc Ogg::ogg)
target_compile_options(theoraenc PRIVATE -O2 -fPIC)

# Combined theora library (includes both dec and enc)
add_library(theora STATIC ${THEORA_DEC_SOURCES} ${THEORA_ENC_SOURCES})
target_link_libraries(theora Ogg::ogg)
target_compile_options(theora PRIVATE -O2 -fPIC)

# Install targets
install(TARGETS theora theoradec theoraenc
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

# Install headers
install(DIRECTORY include/theora/
    DESTINATION include/theora
    FILES_MATCHING PATTERN "*.h"
)

# Set variables for pkg-config file generation
set(VERSION "1.1.1")
set(prefix "${CMAKE_INSTALL_PREFIX}")
set(exec_prefix "\${prefix}")
set(libdir "\${exec_prefix}/lib")
set(includedir "\${prefix}/include")

# Generate pkg-config files
configure_file(theora.pc.in theora.pc @ONLY)
configure_file(theoradec.pc.in theoradec.pc @ONLY)
configure_file(theoraenc.pc.in theoraenc.pc @ONLY)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/theora.pc
    ${CMAKE_CURRENT_BINARY_DIR}/theoradec.pc
    ${CMAKE_CURRENT_BINARY_DIR}/theoraenc.pc
    DESTINATION lib/pkgconfig
)
