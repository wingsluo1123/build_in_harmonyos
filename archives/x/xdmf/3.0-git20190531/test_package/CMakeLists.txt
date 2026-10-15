cmake_minimum_required(VERSION 3.15)
project(test_xdmf CXX)

find_package(Xdmf REQUIRED)
find_package(hdf5 REQUIRED)
find_package(LibXml2 REQUIRED)
find_package(Boost REQUIRED)

add_executable(test_xdmf test_xdmf.cpp)
target_link_libraries(test_xdmf PRIVATE Xdmf::Xdmf)
