cmake_minimum_required(VERSION 3.15)
project(test_gdal CXX)

find_package(GDAL CONFIG REQUIRED)

add_executable(test_gdal test_gdal.cpp)
target_link_libraries(test_gdal PRIVATE GDAL::GDAL)
