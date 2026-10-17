cmake_minimum_required(VERSION 3.15)
project(test_precice CXX)

find_package(precice REQUIRED)

# OHOS stale_runtime_library (2026-10-15): the HarmonyOS loader ignores
# LD_LIBRARY_PATH for consumer binaries, so test_precice failed with
# "Error loading shared library libprecice.so.3" + symbol-not-found even
# though conanrun.sh/LD_PRELOAD pointed at the fresh package. Embed RUNPATH
# at link time so DT_NEEDED resolves without any env var (primary
# mechanism; LD_PRELOAD in conanfile test() stays as fallback only).
set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
set(CMAKE_BUILD_RPATH_USE_ORIGIN TRUE)
# $ORIGIN fallback covers a copy of libprecice placed next to the binary
# by conanfile test(); the absolute package lib dir is appended
# automatically via USE_LINK_PATH at configure time.
set(CMAKE_INSTALL_RPATH "$ORIGIN:$ORIGIN/../lib")
set(CMAKE_BUILD_RPATH "$ORIGIN:$ORIGIN/../lib")
# Explicit linker flags: work even when CMake ships no Platform/HarmonyOS
# module (no RUNTIME-flag variables), unlike the CMAKE_INSTALL_RPATH
# abstraction above.
# --disable-new-dtags (6th route, 20:11 preflight): force DT_RPATH instead
# of DT_RUNPATH. RUNPATH (binutils new-dtags default) does NOT propagate to
# transitive DT_NEEDED (libprecice's own boost/log_setup/xml2/icu deps),
# while RPATH does. OHOS loader ignores LD_LIBRARY_PATH and 20:11 proved
# the LD_PRELOAD chain is also dropped, so propagated RPATH is the only
# remaining transitive channel besides the signed $ORIGIN staging.
add_link_options("LINKER:-rpath,$ORIGIN" "LINKER:-rpath,$ORIGIN/../lib" "LINKER:--disable-new-dtags")

add_executable(test_precice test_precice.cpp)
target_link_libraries(test_precice precice::precice)
target_compile_features(test_precice PRIVATE cxx_std_17)
# Keep the RUNPATH on the build-tree binary as well (ctest/conan run the
# build output directly, never `cmake --install`).
set_target_properties(test_precice PROPERTIES
  BUILD_WITH_INSTALL_RPATH TRUE
  INSTALL_RPATH_USE_LINK_PATH TRUE)

enable_testing()
add_test(NAME test_precice COMMAND test_precice)
