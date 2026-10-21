cmake_minimum_required(VERSION 3.16)

# 本样例是「桌面集成组件必需化」的最小结构复刻（去业务化）：
#   1) REQUIRED 组件表里混入文档工具链 DocTools
#   2) 顶层调用 kdoctools_install(po) 并 add_subdirectory(doc)
#   3) mime 子目录把 SharedMimeInfo 查成 REQUIRED
# 检测脚本应报 6 处 HARD；应用 strategy.md 的 B 策略后为 0 处。

project(kf6-di-sample VERSION 1.0.0 LANGUAGES CXX)

find_package(ECM REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH} ${CMAKE_MODULE_PATH})

include(KDEInstallDirs)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core)
find_package(KF6 6.0 REQUIRED COMPONENTS
    CoreAddons
    DocTools
)

add_executable(kf6-di-sample main.cpp)
target_link_libraries(kf6-di-sample PRIVATE Qt6::Core KF6::CoreAddons)

add_subdirectory(doc)
add_subdirectory(mime)

ki18n_install(po)
kdoctools_install(po)
