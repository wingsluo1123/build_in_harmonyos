cmake_minimum_required(VERSION 3.21)

project(qcustomplot_e2e LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The package is consumed through its installed CMake config, exactly as an
# OHOS application would consume it.
find_package(QCustomPlot CONFIG REQUIRED)

add_executable(test_qcustomplot_e2e test_qcustomplot_e2e.cpp)
target_link_libraries(test_qcustomplot_e2e PRIVATE QCustomPlot::QCustomPlot)

enable_testing()
add_test(NAME test_qcp_e2e COMMAND test_qcustomplot_e2e)
