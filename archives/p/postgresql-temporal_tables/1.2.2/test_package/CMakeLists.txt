cmake_minimum_required(VERSION 3.15)
project(test_temporal_tables C)

# Library path passed from conanfile.py via -DTEMPORAL_TABLES_LIB_PATH
if(NOT TEMPORAL_TABLES_LIB_PATH)
    message(FATAL_ERROR "TEMPORAL_TABLES_LIB_PATH must be set")
endif()

add_executable(test_temporal_tables test.c)
target_compile_definitions(test_temporal_tables PRIVATE
    TEMPORAL_TABLES_LIB_PATH="${TEMPORAL_TABLES_LIB_PATH}"
)

enable_testing()
add_test(NAME test_temporal_tables COMMAND test_temporal_tables)
