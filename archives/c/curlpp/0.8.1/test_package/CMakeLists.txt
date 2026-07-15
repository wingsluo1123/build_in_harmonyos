cmake_minimum_required(VERSION 3.15)
project(test_curlpp CXX)

find_package(curlpp REQUIRED)
find_package(CURL REQUIRED)

add_executable(test_curlpp test.cpp)
target_link_libraries(test_curlpp curlpp::curlpp ${CURL_LIBRARIES})
target_include_directories(test_curlpp PRIVATE ${CURL_INCLUDE_DIRS})

enable_testing()
add_test(NAME test_curlpp COMMAND test_curlpp)
