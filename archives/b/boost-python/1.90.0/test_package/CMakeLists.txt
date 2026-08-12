cmake_minimum_required(VERSION 3.22)
project(boost_python_test_package LANGUAGES CXX)

# boost-python 为独立 cmake_file_name="boost_python"：显式 find_package(boost_python)
# 获得 boost_python::python312（别名 Boost::python312）；同时显式 find_package(Boost)
# 获得 boost/1.90.0.3 的普通头（Boost::headers）——两包共装验证。
find_package(boost_python CONFIG REQUIRED)
find_package(Boost CONFIG REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

# 编译真实 Boost.Python 扩展模块
add_library(test_ext MODULE test_ext.cpp)
target_link_libraries(test_ext PRIVATE boost_python::python312 Boost::headers)
target_include_directories(test_ext PRIVATE ${Python3_INCLUDE_DIRS})
set_target_properties(test_ext PROPERTIES
  PREFIX ""
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
