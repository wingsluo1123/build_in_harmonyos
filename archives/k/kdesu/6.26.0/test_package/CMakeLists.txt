cmake_minimum_required(VERSION 3.15)
project(test_kdesu CXX)

# KF6ConfigTargets.cmake references Qt6::Core/Qt6::Xml targets, so load Qt6
# first (kconfig 6.26.0 test_package precedent).
find_package(Qt6 REQUIRED COMPONENTS Core Xml)
find_package(KF6Su REQUIRED)
find_package(KF6Config REQUIRED)

add_executable(test_kdesu test.cpp)
target_link_libraries(test_kdesu KF6::Su KF6::ConfigCore)

# Locate the kdesu_stub helper installed by the package. KDE_INSTALL_LIBEXECDIR_KF
# resolves under the platform's CMAKE_INSTALL_LIBEXECDIR (measured on the OHOS
# device: <prefix>/bin/kf6), while other ECM releases use libexec, so probe both
# layouts with and without the kf6 suffix, in that priority order. A plain
# file(GLOB)+list(GET 0) cannot express this priority: GLOB returns a
# lexicographically sorted list, so <prefix>/bin/kdesu_stub would win over
# <prefix>/bin/kf6/kdesu_stub. The package always ships the helper, so a
# missing one is a packaging failure: FATAL_ERROR instead of silently
# compiling out the four installation checks (which would leave the test
# green without ever executing the installed binary).
get_filename_component(_kdesu_prefix "${KF6Su_DIR}/../../.." ABSOLUTE)
set(_kdesu_stub "")
foreach(_candidate
  "${_kdesu_prefix}/bin/kf6/kdesu_stub"
  "${_kdesu_prefix}/bin/kdesu_stub"
  "${_kdesu_prefix}/libexec/kf6/kdesu_stub"
  "${_kdesu_prefix}/libexec/kdesu_stub")
  if(NOT _kdesu_stub AND EXISTS "${_candidate}")
    set(_kdesu_stub "${_candidate}")
  endif()
endforeach()
if(NOT _kdesu_stub)
  message(FATAL_ERROR "kdesu_stub not found under ${_kdesu_prefix} (probed bin/kf6, bin, libexec/kf6, libexec)")
endif()
target_compile_definitions(test_kdesu PRIVATE KDESU_TEST_STUB_PATH="${_kdesu_stub}")
message(STATUS "kdesu_stub found at ${_kdesu_stub}")

enable_testing()
add_test(NAME test_kdesu COMMAND test_kdesu)
