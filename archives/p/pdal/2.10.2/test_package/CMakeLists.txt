cmake_minimum_required(VERSION 3.20)
project(test_pdal CXX)

find_package(PDAL REQUIRED)

add_executable(test_pdal test_pdal.cpp)
target_link_libraries(test_pdal PDAL::PDAL)

# Set RPATH for HarmonyOS musl compatibility
set_target_properties(test_pdal PROPERTIES
    BUILD_RPATH "$<TARGET_FILE_DIR:PDAL::PDAL>"
    INSTALL_RPATH "$<TARGET_FILE_DIR:PDAL::PDAL>"
)
