cmake_minimum_required(VERSION 3.15)
project(test_pxr_ts CXX)

find_package(pxr-ts REQUIRED)

add_executable(test_pxr_ts test_pxr_ts.cpp)
target_link_libraries(test_pxr_ts pxr-ts::pxr-ts)
target_compile_features(test_pxr_ts PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_pxr_ts COMMAND test_pxr_ts)
