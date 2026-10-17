cmake_minimum_required(VERSION 3.15)
project(sgb_consumer LANGUAGES C)
find_package(sgb CONFIG REQUIRED)
enable_testing()
add_executable(test_sgb test_sgb.c)
target_compile_definitions(test_sgb PRIVATE SYSV)
target_link_libraries(test_sgb PRIVATE sgb::sgb)
foreach(case core basic shortest serialization random data)
    add_test(NAME consumer_${case} COMMAND test_sgb ${case})
    set_tests_properties(consumer_${case} PROPERTIES TIMEOUT 60)
endforeach()
set_tests_properties(consumer_data PROPERTIES WORKING_DIRECTORY "${SGB_DATA_DIRECTORY}")

# A complete installed-library application workflow, exercised natively on OHOS.
# The two application invocations exchange a persisted graph, not process memory.
add_executable(sgb_route_consumer sgb_route_consumer.c)
target_link_libraries(sgb_route_consumer PRIVATE sgb::sgb)
add_test(NAME harmony_consumer_route_workflow
    COMMAND "${CMAKE_COMMAND}"
        "-DROUTE_APP=$<TARGET_FILE:sgb_route_consumer>"
        "-DROUTE_INPUT=${CMAKE_CURRENT_SOURCE_DIR}/campus-routes.txt"
        "-DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}/HarmonyOS consumer workspace"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/run_route_workflow.cmake")
set_tests_properties(harmony_consumer_route_workflow PROPERTIES TIMEOUT 60)
