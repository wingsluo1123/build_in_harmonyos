# plotsauce 0-0.1 适配笔记

## 软件简介
plotsauce（Debian 包名 plotsauce，版本 0~0.1）是 Cavewhere 生态的 Qt5 命令行
工具，把 Survex .3d 洞穴勘测数据文件转换为 XML。上游仓库
https://github.com/Cavewhere/plotsauce（master 快照，无 release tarball，
无 tag；上游最新提交 173c0304e788fd7b0b06982a4ff9c333ede86eff，2020-03-19）。

## 编译环境
- 构建系统: 上游 QBS（Qt Build Suite）→ 适配改写为 CMake
- 编译日期: 2026-10-17
- 编译器: clang 15（aarch64-linux-ohos）
- 状态: built

## 上游构建系统问题与方案（W0b 历史核验 + dewalls 先例）
上游 plotsauce.qbs 声明依赖 Qt(core,xml,gui)、外部产品 cavern-3dReader、z。
两个关键事实（Debian 打包 0~0.1-1 佐证，sources.debian.org 可核对）：
1. **cavern-3dReader 不在仓库内**（无 submodule、无源码目录）。Debian 的
   plotsauce.qbs 删除了该依赖，并把 `src/survex/*.c`（即 survex 项目的
   img.c/img.h）取消注释加入构建。Debian 内联的 img.h 与 survex **1.2.44**
   官方版逐字节一致（sha256 adca23af...），img.c 仅 3 处防御性微差
   （parser 不受影响）。本配方从 **survex 1.2.44 官方 tarball**（
   https://survex.com/software/1.2.44/survex-1.2.44.tar.gz，R39 官方源）
   取原件 vendored 到 src/survex/，不走 Debian 重打包件（PF7）。
2. **libqmath3d-dev 是 Debian 的残留 Build-Depends**：对 plotsauce 全部
   源码 grep 无任何 qmath/QMath 引用，不需要该依赖。制品仓确认 qmath3d
   未发布（E477 错误文本），本次适配无未发布依赖（W0 ✅）。
3. Qt 组件：源码实际只 include QtCore / QtXml（QDomDocument）；.qbs 声明
   的 gui 无任何源文件使用，CMake 仅链接 Qt5::Core Qt5::Xml。
4. 同仓库生态先例：archives/d/dewalls/1.0.0（同为 Cavewhere/QBS/Qt5），
   采用同样的 "CMakeLists.txt 补丁 + vendored reader" 方案。

## 编译步骤
1. conan create（配方驱动）：source() 下载 plotsauce 快照 + survex 1.2.44
   tarball，vendored img.c/img.h 至 src/survex/；
2. apply patches/0001-CMakeLists.txt.patch（新增 CMake 构建，仅此一个目标）；
3. CMakeToolchain 注入 CMAKE_PREFIX_PATH=qt 包目录（qt/5.15.19 自带
   Qt5Config.cmake，cmake_find_mode=none，dewalls 同款处理）；
4. 无 Q_OBJECT/moc 需求（源码无 Q_OBJECT 宏），无需 AUTOMOC 与宿主 moc 工具。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | .qbs 依赖 cavern-3dReader 不存在 | 上游仓库缺外部产品 | 按 Debian 先例 vendored survex 1.2.44 官方 img.c/img.h |
| 2 | QBS 工具链 | CI 无 QBS | CMakeLists 补丁改写（dewalls 先例） |
| 3 | 上游无测试 | 上游仓库无 tests/ | test_package 端到端补齐（.3d 样例→转换→XML 断言） |

## 源码修改
- patches/0001-CMakeLists.txt.patch：新增 CMakeLists.txt（QBS→CMake 改写）。
- vendored src/survex/img.c、img.h：来自 survex 1.2.44 官方 tarball（conandata
  sources[1]），非源码补丁。

## 依赖版本
- qt/5.15.19（制品仓已发布，W0 核验通过）
- zlib/1.3.1（制品仓已发布）

## 验证结果
见 reports/ 与 .ci-result.json（finish 自动写入）。

## 上游测试清点（R51）
上游仓库 tree（github API 逐项核对）：LICENSE、main.cpp、plotsauce.qbs、
src/（10 个 .cpp/.h）。**无 tests/ 目录、无任何测试注册**（.qbs 未声明测试
产品）。结论：上游确无测试用例，test_package 补齐端到端测试 6 项断言。
---

**编译结束**: 2026-10-17 20:12
**最终状态**: built
