cmake_minimum_required(VERSION 3.15)
project(sox_ng_consumer C)

find_package(sox-ng CONFIG REQUIRED)

add_executable(sox_ng_consumer consumer.c)
target_link_libraries(sox_ng_consumer PRIVATE sox-ng::sox-ng)
set_target_properties(sox_ng_consumer PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Record the compiler-provided OpenMP runtime for the Conan test runner. The
# OHOS device loader does not search the SDK library directory by default.
find_library(SOXNG_OPENMP_RUNTIME NAMES omp
    HINTS ${CMAKE_C_IMPLICIT_LINK_DIRECTORIES}
)
if(NOT SOXNG_OPENMP_RUNTIME)
    message(FATAL_ERROR "Could not locate the compiler OpenMP runtime")
endif()
