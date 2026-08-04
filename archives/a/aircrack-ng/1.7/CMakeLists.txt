cmake_minimum_required(VERSION 3.15)
project(aircrack-ng C CXX)

# Find OpenSSL and zlib via Conan
find_package(OpenSSL REQUIRED)
find_package(ZLIB REQUIRED)

# Include paths
include_directories(
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/lib
    ${CMAKE_SOURCE_DIR}/src
    ${CMAKE_SOURCE_DIR}/include/aircrack-ng/osdep
)

# Compiler definitions
add_definitions(
    -DSTATIC_BUILD
    -DDYNAMIC=0
    -DCACHELINE_SIZE=64
    -Wno-deprecated-declarations
    -Wno-format
)
add_definitions(
    -DABS_TOP_BUILDDIR="."
    -DLIBAIRCRACK_CE_WPA_PATH="."
    -DLT_OBJDIR="."
    -DLIBDIR="${CMAKE_INSTALL_PREFIX}/lib"
)

# Generate version.h from version.h.in
set(VERSION_H_IN ${CMAKE_SOURCE_DIR}/include/aircrack-ng/version.h.in)
set(VERSION_H ${CMAKE_SOURCE_DIR}/include/aircrack-ng/version.h)
if(EXISTS ${VERSION_H_IN} AND NOT EXISTS ${VERSION_H})
    file(READ ${VERSION_H_IN} VERSION_H_CONTENT)
    string(REPLACE "@_MAJ@" "1" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    string(REPLACE "@_MIN@" "7" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    string(REPLACE "@_SUB_MIN@" "0" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    string(REPLACE "@_BETA@" "0" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    string(REPLACE "@_RC@" "0" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    string(REPLACE "@_SCM@" "" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    string(REPLACE "@LT_VER@" "1:7:0" VERSION_H_CONTENT "${VERSION_H_CONTENT}")
    # Add _REVISION define (not in template)
    string(APPEND VERSION_H_CONTENT "\n#define _REVISION \"\"\n")
    file(WRITE ${VERSION_H} "${VERSION_H_CONTENT}")
endif()

# Library source files
set(LIB_SOURCES
    lib/ce-wep/uniqueiv.c
    lib/ce-wpa/crypto_engine.c
    lib/ce-wpa/memory.c
    lib/ce-wpa/simd-intrinsics.c
    lib/ce-wpa/wpapsk.c
    lib/cowpatty/cowpatty.c
    lib/crypto/crypto.c
    lib/ptw/aircrack-ptw-lib.c
    lib/libac/adt/avl_tree.c
    lib/libac/adt/circular_buffer.c
    lib/libac/adt/circular_queue.c
    lib/libac/cpu/simd_cpuid.c
    lib/libac/cpu/trampoline_arm.c
    lib/libac/cpu/cpuset_pthread.c
    lib/libac/support/common.c
    lib/libac/support/crypto_engine_loader.c
    lib/libac/support/mcs_index_rates.c
    lib/libac/support/strlcat.c
    lib/libac/support/strlcpy.c
    lib/libac/tui/console.c
    lib/libac/utf8/verifyssid.c
    lib/radiotap/radiotap.c
    lib/osdep/dummy.c
    lib/osdep/dummy_tap.c
    lib/osdep/common.c
    lib/osdep/network.c
    lib/osdep/osdep.c
    lib/osdep/file.c
)

# Static library from all lib sources
add_library(aircrack_lib STATIC ${LIB_SOURCES})
target_link_libraries(aircrack_lib OpenSSL::Crypto OpenSSL::SSL ZLIB::ZLIB pthread dl)

# Stub for show_wep_stats (needed by aircrack-ptw-lib when not linking with aircrack-ng.c)
add_library(show_wep_stats_stub STATIC build-ohos/stub_show_wep_stats.c)
# Create stub file if it doesn't exist
file(WRITE ${CMAKE_SOURCE_DIR}/build-ohos/stub_show_wep_stats.c
    "#include <stddef.h>\nvoid show_wep_stats(int B, int B2, void *a, void *b, void *c, int force) { (void)B; (void)B2; (void)a; (void)b; (void)c; (void)force; }\n")

# aircrack-ng
add_executable(aircrack-ng
    src/aircrack-ng/aircrack-ng.c
    src/aircrack-ng/linecount.cpp
    src/aircrack-ng/session.c
)
target_link_libraries(aircrack-ng aircrack_lib OpenSSL::Crypto OpenSSL::SSL ZLIB::ZLIB pthread dl m)

# kstats
add_executable(kstats src/kstats/kstats.c)
target_link_libraries(kstats pthread)

# makeivs-ng
add_executable(makeivs-ng src/makeivs-ng/makeivs-ng.c)
target_link_libraries(makeivs-ng aircrack_lib OpenSSL::Crypto OpenSSL::SSL ZLIB::ZLIB pthread dl m)

# Install
install(TARGETS aircrack-ng kstats makeivs-ng RUNTIME DESTINATION bin)
