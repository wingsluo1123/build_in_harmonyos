cmake_minimum_required(VERSION 3.15)
project(test_ocp C)

# Find the package via Conan-generated CMakeDeps
find_package(ocp REQUIRED)

# The package under test is an application: CMakeDeps exposes it as an
# interface target, and test.c exercises the delivered front end itself.
if(NOT DEFINED OCP_BINARY_DIR)
    message(FATAL_ERROR "OCP_BINARY_DIR (the packaged bin directory) must be set")
endif()
set(OCP_BINARY "${OCP_BINARY_DIR}/ocp")
if(NOT EXISTS "${OCP_BINARY}")
    message(FATAL_ERROR "the packaged front end ${OCP_BINARY} does not exist")
endif()

add_executable(test_ocp test.c)
target_link_libraries(test_ocp ocp::ocp)

enable_testing()
add_test(NAME test_ocp COMMAND test_ocp "${OCP_BINARY}")
