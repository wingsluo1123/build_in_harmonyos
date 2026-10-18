cmake_minimum_required(VERSION 3.15)
project(test_plotsauce CXX)

find_package(plotsauce REQUIRED)
find_package(zlib REQUIRED)

# Generates the deterministic Survex .3d input file.
add_executable(test_sample3d test_sample3d.cpp)

# Validates the gzip-compressed XML produced by the packaged plotsauce binary.
add_executable(test_plotsauce test_plotsauce.cpp)
target_link_libraries(test_plotsauce PRIVATE zlib::zlib)

enable_testing()
add_test(NAME make_sample COMMAND test_sample3d ${CMAKE_CURRENT_BINARY_DIR}/test.3d)
add_test(NAME verify_xml COMMAND test_plotsauce ${CMAKE_CURRENT_BINARY_DIR}/out.xml.gz)
