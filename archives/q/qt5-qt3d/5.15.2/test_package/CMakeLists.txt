cmake_minimum_required(VERSION 3.15)
project(test_qt5_qt3d CXX)
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt53D CONFIG REQUIRED)
add_executable(test_qt5_qt3d test.cpp)
target_link_libraries(test_qt5_qt3d PRIVATE Qt5::3DCore Qt5::Core)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qt3d PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qt3d PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qt3d COMMAND $<TARGET_FILE:test_qt5_qt3d>)
