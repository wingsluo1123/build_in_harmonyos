# Independent test runner; upstream executable and golden files are unchanged.
execute_process(COMMAND "${PROGRAM}" WORKING_DIRECTORY "${DATA}"
    OUTPUT_FILE "${DATA}/sample.out" RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
    message(FATAL_ERROR "test_sample returned ${rc}")
endif()
foreach(pair "test.gb;test.correct" "sample.out;sample.correct")
    list(GET pair 0 actual)
    list(GET pair 1 expected)
    execute_process(COMMAND "${CMAKE_COMMAND}" -E compare_files
        "${DATA}/${actual}" "${DATA}/${expected}" RESULT_VARIABLE rc)
    if(NOT rc EQUAL 0)
        message(FATAL_ERROR "Upstream golden comparison failed: ${actual} vs ${expected}")
    endif()
endforeach()
message(STATUS "test_sample and both upstream golden comparisons passed")
