cmake_minimum_required(VERSION 3.15)
project(test_qt5_qtgraphicaleffects CXX)
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5GraphicalEffects CONFIG REQUIRED)
add_executable(test_qt5_qtgraphicaleffects test.cpp)
target_link_libraries(test_qt5_qtgraphicaleffects PRIVATE Qt5::GraphicalEffects Qt5::Core)
if(DEFINED QML_MODULE_DIR)
    target_compile_definitions(test_qt5_qtgraphicaleffects PRIVATE
        QML_MODULE_DIR="${QML_MODULE_DIR}")
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qtgraphicaleffects PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qtgraphicaleffects PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qtgraphicaleffects COMMAND $<TARGET_FILE:test_qt5_qtgraphicaleffects>)
