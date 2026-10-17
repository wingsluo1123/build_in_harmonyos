cmake_minimum_required(VERSION 3.14)
project(dynamorio_test_package C)

# DynamoRIO_DIR is provided by the test_package recipe pointing at the packaged
# cmake/ directory (DynamoRIOConfig.cmake).
find_package(DynamoRIO REQUIRED)

add_executable(dr_standalone_smoke app.c)

# DynamoRIO's standalone helper computes RPATHs from the target's output
# directory at call time, so the property has to be set first (otherwise the
# lookup yields target_loc-NOTFOUND at configure time).
set_target_properties(dr_standalone_smoke PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
configure_DynamoRIO_standalone(dr_standalone_smoke)
