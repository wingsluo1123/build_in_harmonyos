cmake_minimum_required(VERSION 3.15)
project(test_czmq C)

# Find both czmq and its transitive dependency zeromq
find_package(zeromq REQUIRED)
find_package(czmq REQUIRED)

add_executable(test_czmq test.c)
target_link_libraries(test_czmq czmq::czmq zeromq::zeromq)

# Workaround: zeromq include dirs may be empty in CMakeDeps on OHOS
# Get the zeromq include dir from the package folder
if(DEFINED zeromq_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_czmq PRIVATE ${zeromq_PACKAGE_FOLDER_RELEASE}/include)
endif()

enable_testing()
add_test(NAME test_czmq COMMAND test_czmq)
