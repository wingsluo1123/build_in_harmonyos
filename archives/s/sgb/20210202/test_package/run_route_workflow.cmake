cmake_minimum_required(VERSION 3.15)
file(MAKE_DIRECTORY "${WORK_DIR}")
set(graph "${WORK_DIR}/campus.gb")
set(report "${WORK_DIR}/route.txt")
set(rejected_report "${WORK_DIR}/missing-place.txt")
file(REMOVE "${graph}" "${report}" "${rejected_report}")

execute_process(COMMAND "${ROUTE_APP}" import "${ROUTE_INPUT}" "${graph}"
    RESULT_VARIABLE rc)
if(NOT "${rc}" STREQUAL "0" OR NOT EXISTS "${graph}")
    message(FATAL_ERROR "Consumer failed to import and persist the route graph: ${rc}")
endif()
# A separate process must recover the actual serialized graph from the filesystem.
execute_process(COMMAND "${ROUTE_APP}" solve "${graph}" Entrance Lab "${report}"
    RESULT_VARIABLE rc)
if(NOT "${rc}" STREQUAL "0" OR NOT EXISTS "${report}")
    message(FATAL_ERROR "Consumer failed to restore, solve and export the route: ${rc}")
endif()
file(READ "${report}" actual)
set(expected "distance=9\npath=Entrance -> Hall -> Lift -> Lab\n")
if(NOT "${actual}" STREQUAL "${expected}")
    message(FATAL_ERROR "Incorrect consumer route report: ${actual}")
endif()
execute_process(COMMAND "${ROUTE_APP}" solve "${graph}" Entrance Missing
    "${rejected_report}" RESULT_VARIABLE rc)
if(NOT "${rc}" STREQUAL "1" OR EXISTS "${rejected_report}")
    message(FATAL_ERROR "Unknown destination must fail without a successful report: ${rc}")
endif()
message(STATUS "PASS native consumer workflow: import -> persist -> restore -> route -> report")
