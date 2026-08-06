cmake_minimum_required(VERSION 3.15)
project(test_pipeline C)

find_package(libpipeline REQUIRED)

add_executable(test_pipeline test_pipeline.c)
target_link_libraries(test_pipeline libpipeline::libpipeline)

enable_testing()
add_test(NAME test_pipeline COMMAND test_pipeline)
