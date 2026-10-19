cmake_minimum_required(VERSION 3.16)
project(wvkbd_core VERSION 0.15 LANGUAGES C)

option(WVKBD_BUILD_TESTS "Build portable keyboard core tests" OFF)
add_library(wvkbd_core STATIC src/wvkbd_core.c src/layout_mobintl.c)
add_library(wvkbd::core ALIAS wvkbd_core)
target_compile_features(wvkbd_core PUBLIC c_std_11)
set_target_properties(wvkbd_core PROPERTIES C_EXTENSIONS OFF POSITION_INDEPENDENT_CODE ON)
target_include_directories(wvkbd_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
include(GNUInstallDirs)
install(TARGETS wvkbd_core ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES include/wvkbd_core.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

if(WVKBD_BUILD_TESTS)
    enable_testing()
    add_executable(wvkbd_core_tests tests/test_core.c tests/core_cases.c)
    target_link_libraries(wvkbd_core_tests PRIVATE wvkbd_core)
    foreach(test_name IN ITEMS
        test_default_layout_has_printable_and_control_keys
        test_shift_caps_and_emitted_character
        test_invalid_key_coordinates_and_null_arguments
        test_layout_strings_are_valid_utf8)
        add_test(NAME ${test_name} COMMAND wvkbd_core_tests ${test_name})
    endforeach()
endif()
