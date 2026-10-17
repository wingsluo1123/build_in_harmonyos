cmake_minimum_required(VERSION 3.15)
project(test_ocl_icd C)

find_package(OpenCL REQUIRED)
find_package(opencl-headers REQUIRED)

# The fixture supplies a vendor boundary; the executable calls the installed
# OpenCL::OpenCL loader, which must discover and dispatch to that vendor.
add_library(test_icd SHARED test_icd.c)
target_link_libraries(test_icd PRIVATE opencl-headers::opencl-headers)
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/empty-vendors")

add_executable(test_ocl_icd test.c)
target_link_libraries(test_ocl_icd OpenCL::OpenCL opencl-headers::opencl-headers)
target_compile_definitions(test_ocl_icd PRIVATE
    TEST_ICD_PATH="$<TARGET_FILE:test_icd>"
    EMPTY_VENDOR_DIR="${CMAKE_CURRENT_BINARY_DIR}/empty-vendors")
add_dependencies(test_ocl_icd test_icd)

enable_testing()
add_test(NAME test_ocl_icd_empty COMMAND test_ocl_icd empty)
add_test(NAME test_ocl_icd_fixture COMMAND test_ocl_icd fixture)
