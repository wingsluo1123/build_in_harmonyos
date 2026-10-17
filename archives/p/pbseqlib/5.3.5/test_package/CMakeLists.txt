cmake_minimum_required(VERSION 3.15)
project(test_pbseqlib CXX)

# Explicit full-static consumer route (2026-10-15, 2nd fix of this
# fingerprint): LD_LIBRARY_PATH, LD_PRELOAD, absolute RPATH and the
# --as-needed static-first variant all left the same `Error relocating
# DNASequence/TwoBit/ThreeBit` fingerprint, because every one of them kept
# a DT_NEEDED entry on libblasr.so whose runtime resolution the OHOS loader
# controls. This branch links NO shared blasr at all: the three static
# archives (libblasr.a + the merged libpbbam.a/libpbcopper.a) by full path,
# wrapped in --start-group/--end-group for archive cycles, plus the
# transitive deps (hdf5/htslib/zlib/boost plus htslib's xz/libdeflate and any
# other host dep) as explicit files and the
# system libs as -l flags. The resulting binary has no DT_NEEDED on
# libblasr, so the loader never opens it. find_package(libblasr) is kept
# ONLY for its INTERFACE include directories and compile definitions.
# Missing static inputs are a hard FATAL_ERROR with the searched paths
# (honest fail-fast); silently falling back to the known-broken shared path
# is refused.
if(DEFINED PBSEQLIB_EXTRA_RPATH AND NOT PBSEQLIB_EXTRA_RPATH STREQUAL "")
  set(CMAKE_BUILD_RPATH "${PBSEQLIB_EXTRA_RPATH}")
  set(CMAKE_INSTALL_RPATH "${PBSEQLIB_EXTRA_RPATH}")
  set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)
endif()
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

find_package(libblasr CONFIG REQUIRED)

add_executable(test_pbseqlib test_pbseqlib.cpp)
if(DEFINED PBSEQLIB_STATIC_LIB AND EXISTS "${PBSEQLIB_STATIC_LIB}"
   AND DEFINED PBSEQLIB_STATIC_PBBAM AND EXISTS "${PBSEQLIB_STATIC_PBBAM}"
   AND DEFINED PBSEQLIB_STATIC_PBCOPPER AND EXISTS "${PBSEQLIB_STATIC_PBCOPPER}"
   AND DEFINED PBSEQLIB_TRANSITIVE_LIBS)
  message(STATUS "pbseqlib test: explicit static link")
  message(STATUS "pbseqlib test: blasr=${PBSEQLIB_STATIC_LIB}")
  message(STATUS "pbseqlib test: pbbam=${PBSEQLIB_STATIC_PBBAM}")
  message(STATUS "pbseqlib test: pbcopper=${PBSEQLIB_STATIC_PBCOPPER}")
  target_include_directories(test_pbseqlib PRIVATE
    $<TARGET_PROPERTY:libblasr::libblasr,INTERFACE_INCLUDE_DIRECTORIES>)
  target_compile_definitions(test_pbseqlib PRIVATE
    $<TARGET_PROPERTY:libblasr::libblasr,INTERFACE_COMPILE_DEFINITIONS>)
  target_link_libraries(test_pbseqlib PRIVATE
    "LINKER:--start-group"
    "${PBSEQLIB_STATIC_LIB}"
    "${PBSEQLIB_STATIC_PBBAM}"
    "${PBSEQLIB_STATIC_PBCOPPER}"
    ${PBSEQLIB_TRANSITIVE_LIBS}
    "LINKER:--end-group")
else()
  message(FATAL_ERROR
    "pbseqlib test: static archives incomplete "
    "(blasr=${PBSEQLIB_STATIC_LIB} pbbam=${PBSEQLIB_STATIC_PBBAM} "
    "pbcopper=${PBSEQLIB_STATIC_PBCOPPER}); refusing the shared fallback "
    "that fails on the OHOS loader with Error relocating DNASequence/TwoBit")
endif()
