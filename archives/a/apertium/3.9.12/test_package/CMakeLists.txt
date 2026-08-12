cmake_minimum_required(VERSION 3.15)
project(apertium_smoke_test LANGUAGES CXX)

find_package(apertium REQUIRED CONFIG)
find_package(utf8cpp REQUIRED CONFIG)
find_package(icu4c REQUIRED CONFIG)
find_package(lttoolbox REQUIRED CONFIG)

add_executable(apertium_probe apertium_probe.cpp)
# lttoolbox's ustring.o references ICU's versioned u_fprintf_77 symbol which
# lives in libicuio.a; icu4c Conan package's cpp_info.libs omits icuio+icutu.
# Link the missing ICU libs explicitly via find_library so the test target
# resolves u_fprintf_77 and related ICU io/tu symbols.
# test_package conanfile generate() writes the icu4c lib dir to icu4c_lib.txt.
get_filename_component(_build_dir "${CMAKE_BINARY_DIR}" DIRECTORY)
get_filename_component(_build_dir "${_build_dir}" DIRECTORY)
set(_icu4c_lib_dir "")
if(EXISTS "${CMAKE_BINARY_DIR}/icu4c_lib.txt")
    file(READ "${CMAKE_BINARY_DIR}/icu4c_lib.txt" _icu4c_lib_dir)
    string(STRIP "${_icu4c_lib_dir}" _icu4c_lib_dir)
elseif(EXISTS "${_build_dir}/icu4c_lib.txt")
    file(READ "${_build_dir}/icu4c_lib.txt" _icu4c_lib_dir)
    string(STRIP "${_icu4c_lib_dir}" _icu4c_lib_dir)
endif()
if(_icu4c_lib_dir)
    find_library(ICUIO_LIB icuio PATHS "${_icu4c_lib_dir}" NO_DEFAULT_PATH)
    find_library(ICUTU_LIB icutu PATHS "${_icu4c_lib_dir}" NO_DEFAULT_PATH)
    find_library(ICUI18N_LIB icui18n PATHS "${_icu4c_lib_dir}" NO_DEFAULT_PATH)
    find_library(ICUUC_LIB icuuc PATHS "${_icu4c_lib_dir}" NO_DEFAULT_PATH)
    find_library(ICUDATA_LIB icudata PATHS "${_icu4c_lib_dir}" NO_DEFAULT_PATH)
endif()
target_link_libraries(apertium_probe PRIVATE
    apertium::apertium
    lttoolbox::lttoolbox
    utf8cpp::utf8cpp
    icu4c::icu4c
    ${ICUIO_LIB}
    ${ICUTU_LIB}
    ${ICUI18N_LIB}
    ${ICUUC_LIB}
    ${ICUDATA_LIB}
)

# lttoolbox's ustring.h includes <utf8.h> (bare header name) which lives
# in utf8cpp's include/utf8cpp/ subdir. CMakeDeps exposes utf8cpp::utf8cpp
# but its INTERFACE_INCLUDE_DIRECTORIES points to include/ (not include/utf8cpp/).
# The test_package conanfile generate() writes the utf8cpp/ subdir path to
# utf8cpp_inc.txt in the build folder; read it and add to include search path.
get_filename_component(_build_dir "${CMAKE_BINARY_DIR}" DIRECTORY)
get_filename_component(_build_dir "${_build_dir}" DIRECTORY)
set(_utf8cpp_inc_file "${CMAKE_BINARY_DIR}/utf8cpp_inc.txt")
if(NOT EXISTS "${_utf8cpp_inc_file}")
    set(_utf8cpp_inc_file "${_build_dir}/utf8cpp_inc.txt")
endif()
if(EXISTS "${_utf8cpp_inc_file}")
    file(READ "${_utf8cpp_inc_file}" _utf8cpp_subdir)
    string(STRIP "${_utf8cpp_subdir}" _utf8cpp_subdir)
    if(EXISTS "${_utf8cpp_subdir}/utf8.h")
        target_include_directories(apertium_probe PRIVATE "${_utf8cpp_subdir}")
    endif()
endif()
# Fallback: probe utf8cpp::utf8cpp INTERFACE_INCLUDE_DIRECTORIES too.
if(TARGET utf8cpp::utf8cpp)
    get_target_property(_utf8cpp_iface utf8cpp::utf8cpp INTERFACE_INCLUDE_DIRECTORIES)
    if(_utf8cpp_iface)
        foreach(_inc ${_utf8cpp_iface})
            if(EXISTS "${_inc}/utf8cpp/utf8.h")
                target_include_directories(apertium_probe PRIVATE "${_inc}/utf8cpp")
            endif()
        endforeach()
    endif()
endif()

enable_testing()
add_test(NAME apertium_probe COMMAND apertium_probe)
