cmake_minimum_required(VERSION 3.15)
project(test_qtremoteobjects CXX)

# 运行时测试：链接 Qt5 + qtremoteobjects
# OHOS 上需要未 strip 的 Qt5 库 + RPATH 才能运行
find_package(qtremoteobjects REQUIRED)

add_executable(test_qtremoteobjects test.cpp)
target_link_libraries(test_qtremoteobjects qtremoteobjects::qtremoteobjects)

# 设置 RPATH 使运行时能找到所有依赖库
# 使用 DT_RPATH (not DT_RUNPATH) 因为 musl 不传递 RUNPATH 到间接依赖
set_target_properties(test_qtremoteobjects PROPERTIES
    BUILD_RPATH "$<TARGET_FILE_DIR:test_qtremoteobjects>"
    INSTALL_RPATH "$<TARGET_FILE_DIR:test_qtremoteobjects>"
    LINK_FLAGS "-Wl,--disable-new-dtags"
)

enable_testing()
add_test(NAME test_qtremoteobjects COMMAND test_qtremoteobjects)
