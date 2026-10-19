cmake_minimum_required(VERSION 3.16)
project(wvkbd_consumer LANGUAGES C)
find_package(wvkbd CONFIG REQUIRED)
if(NOT EXISTS "${WVKBD_TEST_SUPPORT_DIR}/core_cases.c")
    message(FATAL_ERROR "WVKBD_TEST_SUPPORT_DIR must point to the packaged test-support resource")
endif()
# These test-only sources come from the installed package; both harnesses use
# the same case implementation. The product HAP does not compile this target.
set(shared_cases "${WVKBD_TEST_SUPPORT_DIR}/core_cases.c")
add_library(wvkbd_test_consumer STATIC test_consumer.c "${shared_cases}")
set_target_properties(wvkbd_test_consumer PROPERTIES POSITION_INDEPENDENT_CODE ON)
# The separate editor HAP imports this exact archive; shared cases are compiled
# once here from the installed package rather than copied into the editor.
target_compile_features(wvkbd_test_consumer PUBLIC c_std_11)
target_include_directories(wvkbd_test_consumer PRIVATE "${WVKBD_TEST_SUPPORT_DIR}")
target_link_libraries(wvkbd_test_consumer PUBLIC wvkbd::core)
add_executable(wvkbd_consumer test_consumer.c "${shared_cases}")
target_compile_definitions(wvkbd_consumer PRIVATE WVKBD_TEST_CONSUMER_MAIN)
target_include_directories(wvkbd_consumer PRIVATE "${WVKBD_TEST_SUPPORT_DIR}")
target_link_libraries(wvkbd_consumer PRIVATE wvkbd::core)
enable_testing()
add_test(NAME packaged_core_behavior COMMAND wvkbd_consumer)
