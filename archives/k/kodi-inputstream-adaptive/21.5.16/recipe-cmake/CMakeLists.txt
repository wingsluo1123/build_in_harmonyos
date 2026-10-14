cmake_minimum_required(VERSION 3.15)
# Standalone build entry for the inputstream.adaptive add-on sources.
#
# The upstream CMakeLists.txt needs the Kodi build system
# (find_package(Kodi REQUIRED) -> build_addon(), KODI_INCLUDE_DIR) which does
# not exist in this environment; this file builds the same unmodified sources
# as a shared module against Conan CMakeDeps targets instead
# (kodi-inputstream-rtmp/21.1.2 + kodi-platform precedent):
#
# - the tarball Helpers.cmake macros (add_dir_sources/source_group_by_folder)
#   are reused verbatim, and the upstream src/ subdirectory CMakeLists files
#   declare their file lists into the same GLOBAL properties they always do;
# - this file only replaces the Kodi build_addon() call with its own SHARED
#   module target and a SONAME flag (CI L5a), and wires the real upstream
#   gtest suite (src/test) with CTest.
project(inputstream.adaptive LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/..")
# Vendored Kodi C++ add-on headers (kodi-dev-kit), verbatim from
# xbmc 21.3-Omega xbmc/addons/kodi-dev-kit/include/kodi (its kodi/ subtree is
# vendored one level up as kodi-dev-kit/kodi so that <kodi/...> resolves).
set(KODI_DEV_KIT_INCLUDE "${CMAKE_CURRENT_SOURCE_DIR}/../kodi-dev-kit")

include("${SRC_DIR}/Helpers.cmake")

# --------------------------------------------------------------------------
# Dependencies (Conan CMakeDeps; upstream Findpugixml/FindRAPIDJSON map 1:1
# onto CONFIG packages — same find_path/find_library content)
# --------------------------------------------------------------------------
find_package(pugixml CONFIG REQUIRED)
find_package(rapidjson CONFIG REQUIRED)
find_package(Threads REQUIRED) # upstream src/test links Threads::Threads

# --------------------------------------------------------------------------
# Bento4 — vendored xbmc fork built in-tree as a static PIC archive
#
# Upstream: depends/common/bento4 pins the xbmc fork 1.6.0-641-3-Omega and
# FindBento4.cmake (ENABLE_INTERNAL_BENTO4) builds it with an explicit -fPIC
# because the static libap4.a is linked INTO the dlopen module. This mirrors
# that: conanfile.source() extracts the pinned fork to <source>/bento4 and we
# define the same static library here. Every archive linked into the shared
# module must be position independent (non-PIC archives fail on aarch64:
# R_AARCH64 relocation errors).
# --------------------------------------------------------------------------
set(BENTO4_SRC "${SRC_DIR}/bento4")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
file(GLOB AP4_SOURCES
     "${BENTO4_SRC}/Source/C++/Codecs/*.cpp"
     "${BENTO4_SRC}/Source/C++/Core/*.cpp"
     "${BENTO4_SRC}/Source/C++/Crypto/*.cpp"
     "${BENTO4_SRC}/Source/C++/MetaData/*.cpp"
     "${BENTO4_SRC}/Source/C++/System/StdC/*.cpp"
     "${BENTO4_SRC}/Source/C++/System/Posix/Ap4PosixRandom.cpp")
# ISA code includes <bento4/Ap4.h> (upstream install layout: include/bento4/).
# Stage the fork headers under a bento4/ prefix so the include style matches.
set(BENTO4_STAGED_INCLUDE "${CMAKE_BINARY_DIR}/bento4-staged/include")
file(GLOB AP4_PUBLIC_HEADERS
     "${BENTO4_SRC}/Source/C++/Core/*.h"
     "${BENTO4_SRC}/Source/C++/Codecs/*.h"
     "${BENTO4_SRC}/Source/C++/Crypto/*.h"
     "${BENTO4_SRC}/Source/C++/MetaData/*.h")
file(COPY ${AP4_PUBLIC_HEADERS} DESTINATION "${BENTO4_STAGED_INCLUDE}/bento4")
add_library(ap4 STATIC ${AP4_SOURCES})
target_include_directories(ap4 PUBLIC
                           "${BENTO4_STAGED_INCLUDE}"
                           "${BENTO4_SRC}/Source/C++/Core"
                           "${BENTO4_SRC}/Source/C++/Codecs"
                           "${BENTO4_SRC}/Source/C++/Crypto"
                           "${BENTO4_SRC}/Source/C++/MetaData")

# --------------------------------------------------------------------------
# Add-on module: consume the upstream-declared source lists
# --------------------------------------------------------------------------
add_subdirectory("${SRC_DIR}/src" "${CMAKE_BINARY_DIR}/src-build")
get_property(ADP_SOURCES GLOBAL PROPERTY GlobalSourceList)
# widevine registers its in-tree native CDM library through the upstream
# add_dependency() mechanism (GlobalDepsFoldersList = lib/cdm). The separate
# cdm_aarch64_loader SHARED helper is only registered by upstream when
# CMAKE_SYSTEM_NAME is Linux — HarmonyOS keeps the upstream behavior of not
# building it.
get_property(DEPS_FOLDERS_LIST GLOBAL PROPERTY GlobalDepsFoldersList)
set(DEP_INDEX 0)
foreach(DEP_FOLDER ${DEPS_FOLDERS_LIST})
  math(EXPR DEP_INDEX "${DEP_INDEX} + 1")
  add_subdirectory("${SRC_DIR}/${DEP_FOLDER}" "${CMAKE_BINARY_DIR}/dep-${DEP_INDEX}")
endforeach()
get_property(DEPS_NAMES_LIST GLOBAL PROPERTY GlobalDepsNamesList)

# In-tree static libs with their own upstream CMakeLists (PIC already set by
# them).
add_subdirectory("${SRC_DIR}/lib/mpegts" "${CMAKE_BINARY_DIR}/mpegts")
add_subdirectory("${SRC_DIR}/lib/webm_parser" "${CMAKE_BINARY_DIR}/webm_parser")

add_library(inputstream.adaptive SHARED ${ADP_SOURCES})
target_include_directories(inputstream.adaptive PRIVATE
                           "${SRC_DIR}/src"
                           "${KODI_DEV_KIT_INCLUDE}")
# Required on some old linux platforms to use macro like PRIu64 (upstream).
target_compile_definitions(inputstream.adaptive PRIVATE __STDC_FORMAT_MACROS)
target_link_libraries(inputstream.adaptive PRIVATE
                      ap4
                      pugixml::pugixml
                      rapidjson::rapidjson
                      mpegts
                      webm_parser
                      ${DEPS_NAMES_LIST}
                      ${CMAKE_DL_LIBS})

# The OHOS/HarmonyOS platform module in CMake does not define the soname
# flag (Android-style), so shared libraries come out without DT_SONAME;
# set it explicitly (CI L5a quality gate requires a relative DT_SONAME).
target_link_options(inputstream.adaptive PRIVATE "-Wl,-soname,libinputstream.adaptive.so")

include(GNUInstallDirs)
install(TARGETS inputstream.adaptive
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

# --------------------------------------------------------------------------
# Upstream gtest suite (src/test), real run via CTest
#
# The suite is compiled with -DINPUTSTREAM_TEST_BUILD: every Kodi include in
# the production sources is routed to src/test/KodiStubs.h stubs (include
# "test/KodiStubs.h" resolved through ${SRC_DIR}/src), so no Kodi host or
# headers are needed. add_test passes the manifests fixtures directory as
# DATADIR, exactly like upstream (offline, no network).
# --------------------------------------------------------------------------
enable_testing()
add_executable(inputstream.adaptive_test
               "${SRC_DIR}/src/test/TestMain.cpp"
               "${SRC_DIR}/src/test/TestDASHTree.cpp"
               "${SRC_DIR}/src/test/TestHLSTree.cpp"
               "${SRC_DIR}/src/test/TestSmoothTree.cpp"
               "${SRC_DIR}/src/test/TestHelper.cpp"
               "${SRC_DIR}/src/test/TestUtils.cpp"
               "${SRC_DIR}/src/decrypters/Helpers.cpp"
               "${SRC_DIR}/src/parser/DASHTree.cpp"
               "${SRC_DIR}/src/parser/HLSTree.cpp"
               "${SRC_DIR}/src/parser/SmoothTree.cpp"
               "${SRC_DIR}/src/parser/PRProtectionParser.cpp"
               "${SRC_DIR}/src/common/AdaptationSet.cpp"
               "${SRC_DIR}/src/common/AdaptiveStream.cpp"
               "${SRC_DIR}/src/common/AdaptiveTree.cpp"
               "${SRC_DIR}/src/common/AdaptiveTreeFactory.cpp"
               "${SRC_DIR}/src/common/AdaptiveUtils.cpp"
               "${SRC_DIR}/src/common/Chooser.cpp"
               "${SRC_DIR}/src/common/ChooserAskQuality.cpp"
               "${SRC_DIR}/src/common/ChooserDefault.cpp"
               "${SRC_DIR}/src/common/ChooserFixedRes.cpp"
               "${SRC_DIR}/src/common/ChooserManualOSD.cpp"
               "${SRC_DIR}/src/common/ChooserTest.cpp"
               "${SRC_DIR}/src/common/CommonAttribs.cpp"
               "${SRC_DIR}/src/common/CommonSegAttribs.cpp"
               "${SRC_DIR}/src/common/Period.cpp"
               "${SRC_DIR}/src/common/Representation.cpp"
               "${SRC_DIR}/src/common/ReprSelector.cpp"
               "${SRC_DIR}/src/common/Segment.cpp"
               "${SRC_DIR}/src/common/SegmentBase.cpp"
               "${SRC_DIR}/src/common/SegmentList.cpp"
               "${SRC_DIR}/src/common/SegTemplate.cpp"
               "${SRC_DIR}/src/oscompat.cpp"
               "${SRC_DIR}/src/SrvBroker.cpp"
               "${SRC_DIR}/src/CompSettings.cpp"
               "${SRC_DIR}/src/CompKodiProps.cpp"
               "${SRC_DIR}/src/utils/Base64Utils.cpp"
               "${SRC_DIR}/src/utils/CharArrayParser.cpp"
               "${SRC_DIR}/src/utils/CurlUtils.cpp"
               "${SRC_DIR}/src/utils/DigestMD5Utils.cpp"
               "${SRC_DIR}/src/utils/FileUtils.cpp"
               "${SRC_DIR}/src/utils/StringUtils.cpp"
               "${SRC_DIR}/src/utils/UrlUtils.cpp"
               "${SRC_DIR}/src/utils/Utils.cpp"
               "${SRC_DIR}/src/utils/XMLUtils.cpp")

find_package(gtest CONFIG REQUIRED)
target_compile_definitions(inputstream.adaptive_test PRIVATE
                           INPUTSTREAM_TEST_BUILD
                           __STDC_FORMAT_MACROS)
target_include_directories(inputstream.adaptive_test PRIVATE
                           "${SRC_DIR}/src"
                           "${KODI_DEV_KIT_INCLUDE}")
target_link_libraries(inputstream.adaptive_test PRIVATE
                      ap4
                      pugixml::pugixml
                      rapidjson::rapidjson
                      gtest::gtest
                      Threads::Threads
                      ${CMAKE_DL_LIBS})

set(TEST_DATA_DIR "${SRC_DIR}/src/test/manifests")
add_test(NAME manifest_tests COMMAND inputstream.adaptive_test "${TEST_DATA_DIR}")
