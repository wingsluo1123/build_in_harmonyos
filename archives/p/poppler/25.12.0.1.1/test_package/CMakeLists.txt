cmake_minimum_required(VERSION 3.15)
project(test_poppler CXX)

# Find the package via Conan-generated CMakeDeps
find_package(poppler REQUIRED)

# Qt5 绑定测试需要 Qt5 头/库（libpoppler-qt5 链接 Qt5::Core/Qt5::Gui/Qt5::Xml）。
# 依赖由 poppler 的 requirements(qt5-qtbase) 经 CMakeDeps 提供配置。
# 注意：必须是单个 find_package(Qt5)，不能拆成 find_package(Qt5Core/Qt5Gui/Qt5Xml)——
# CMakeDeps 只按**包级** cmake_file_name 生成配置文件，qt5-qtbase 的包级名为 Qt5，
# 故只产出 Qt5Config.cmake（组件级 cmake_file_name 不生成独立 Qt5CoreConfig.cmake），
# 拆开写会在 configure 阶段报 "Could not find a package configuration file for Qt5Core"。
# 该用法与已合入主干的 archives/q/qt5-qtbase/5.15.2.1/test_package/CMakeLists.txt 一致。
find_package(Qt5 CONFIG REQUIRED)

# ── poppler-cpp 绑定测试（真实解析 PDF，见 test.cpp 头部 R34 说明）────────────
add_executable(test_poppler test.cpp)
target_link_libraries(test_poppler poppler::poppler)

# ── poppler-qt5 绑定测试（F4：覆盖本 PR 启用的 Qt5 绑定，renderToImage 渲染）──
add_executable(test_poppler_qt5 test_qt5.cpp)
target_link_libraries(test_poppler_qt5 poppler::poppler Qt5::Core Qt5::Gui Qt5::Xml)

enable_testing()
add_test(NAME test_poppler COMMAND test_poppler)
add_test(NAME test_poppler_qt5 COMMAND test_poppler_qt5)
