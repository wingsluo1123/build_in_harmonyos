# 样例：最小复刻「桌面会话双分支」结构（kwrited 6.7.2 的去业务化版本）
#
# 目的（纯演示，不属于任何交付制品）：
#   1) 「关策略」：`SAMPLE_ASSUME_DESKTOP_SESSION=1`（见下方演示专用开关）时，走会话插件分支
#      —— 该分支要求 KF6::DBusAddons 且产物要装进 plugins/kf6/kded/，在 OHOS 上既拿不到依赖、
#      也没有任何装载路径，配置阶段即失败；
#      注：命令行 -DBUILD_AS_EXECUTABLE=OFF **无效**——KF6PtyConfig 用普通变量导出
#      KPty_HAVE_UTEMPTER，会遮蔽命令行 -D（原因见下方开关处的说明）。
#   2) 「开策略」：默认配置下，KF6Pty 包导出的 KPty_HAVE_UTEMPTER=FALSE 通过
#      cmake_dependent_option 把 BUILD_AS_EXECUTABLE 强制为 ON —— 走独立可执行
#      分支，配置与编译都成功（这也是 kwrited 在 OHOS 上的真实形态）。
#
# 结构逐字同构于 kwrited 6.7.2：
#   cmake_dependent_option(BUILD_AS_EXECUTABLE "Whether to build kwrited as executable" OFF
#       "KPty_HAVE_UTEMPTER" ON)
cmake_minimum_required(VERSION 3.16)

project(session_strategy_sample
    VERSION 1.0.0
    DESCRIPTION "Minimal replica of the KDED-plugin / standalone-executable dual branch"
    LANGUAGES CXX)

set(QT_MIN_VERSION "6.10.0")
set(KF6_MIN_VERSION "6.26.0")

find_package(ECM ${KF6_MIN_VERSION} REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH} ${CMAKE_MODULE_PATH})
# 安装目录用 GNUInstallDirs，**不引入 KDEInstallDirs**：ECM 6.26 的 KDEInstallDirs
# （Qt6 分支）会在配置期强制查询**可运行的** Qt6 qtpaths，而交叉编译到 OHOS 时唯一可用的
# qtpaths 是 aarch64 二进制、宿主跑不起来 → 配置必然 FATAL。样例只演示会话/KDED 分支策略，
# 安装目录规则从简即可（真实上游 kwrited 用 KDEInstallDirs + KDE_INSTALL_*）。
include(GNUInstallDirs)
include(KDECompilerSettings NO_POLICY_SCOPE)

find_package(Qt6 ${QT_MIN_VERSION} REQUIRED COMPONENTS Core)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS CoreAddons Pty)

# ⇩ 与 kwrited 上游同构的联动开关：KPty_HAVE_UTEMPTER 由 KF6Pty 包配置导出，
#   为假时该选项被强制为 ON（注意第四参数 "KPty_HAVE_UTEMPTER"、第五参数 ON）。
#   cmake_dependent_option 来自 CMakeDependentOption 模块，上游 kwrited 同样显式
#   include（ECM/KDECompilerSettings 不代为引入，缺它会在配置期报 Unknown CMake command）。
include(CMakeDependentOption)
cmake_dependent_option(BUILD_AS_EXECUTABLE
    "Whether to build the sample as a standalone executable instead of a session plugin"
    OFF "KPty_HAVE_UTEMPTER" ON)

# 演示专用开关（真实上游 kwrited 没有这一句）：把「本平台有桌面会话 / KDED」这一假设
# 强行打开，用于复现「关策略」分支。必须放在 cmake_dependent_option 之后才能覆盖联动结果
# （KF6PtyConfig 用普通变量导出 KPty_HAVE_UTEMPTER，命令行 -D 覆盖会被它遮蔽）。
if (SAMPLE_ASSUME_DESKTOP_SESSION)
    set(BUILD_AS_EXECUTABLE OFF CACHE BOOL "forced by SAMPLE_ASSUME_DESKTOP_SESSION" FORCE)
endif()

message(STATUS "session-strategy sample: KPty_HAVE_UTEMPTER=${KPty_HAVE_UTEMPTER} "
               "BUILD_AS_EXECUTABLE=${BUILD_AS_EXECUTABLE}")

if (BUILD_AS_EXECUTABLE)
    add_executable(session_strategy_sample main.cpp)
    target_link_libraries(session_strategy_sample PRIVATE Qt6::Core KF6::CoreAddons KF6::Pty)
    install(TARGETS session_strategy_sample RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
else()
    # 会话插件分支：需要 KDED 装载。OHOS 无 KDED，产物永不加载 —— 本分支存在的
    # 意义就是让「关策略」成为一种可复现的配置失败，而不是一个静默无用的 .so。
    find_package(KF6DBusAddons ${KF6_MIN_VERSION} REQUIRED)
    add_library(session_strategy_sample MODULE main.cpp)
    target_compile_definitions(session_strategy_sample PRIVATE SAMPLE_PLUGIN_BRANCH)
    target_link_libraries(session_strategy_sample PRIVATE
        Qt6::Core KF6::CoreAddons KF6::Pty KF6::DBusAddons)
    install(TARGETS session_strategy_sample LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}/plugins/kf6/kded)
    install(FILES sample-session-plugin.json DESTINATION ${CMAKE_INSTALL_LIBDIR}/plugins/kf6/kded)
endif()
