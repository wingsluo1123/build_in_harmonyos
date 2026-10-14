cmake_minimum_required(VERSION 3.15)
project(test_gocr CXX)

# libPgm2asc is a C library; the consumer is C++ (OSRA).  The headers have no
# extern "C" guards of their own, so consumers must wrap the includes - which
# is exactly what test_gocr.cpp does.
find_package(gocr REQUIRED)

add_executable(test_gocr test_gocr.cpp)
target_link_libraries(test_gocr gocr::gocr)
