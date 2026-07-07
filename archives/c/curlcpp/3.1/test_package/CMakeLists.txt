cmake_minimum_required(VERSION 3.15)
project(test_curlcpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(curlcpp REQUIRED)

# Fallback: find system curl headers when curl@ohpcd/stable is not available
find_path(SYSTEM_CURL_INCLUDE_DIR NAMES curl/curl.h
    PATHS $ENV{HOME}/usr/local/include /usr/include /usr/local/include)

add_executable(test_curlcpp test.cpp)
target_link_libraries(test_curlcpp curlcpp::curlcpp)

# Add system curl include path for transitive header dependency
if(SYSTEM_CURL_INCLUDE_DIR)
    target_include_directories(test_curlcpp PRIVATE ${SYSTEM_CURL_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_curlcpp COMMAND test_curlcpp)
