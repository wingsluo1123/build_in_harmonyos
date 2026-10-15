# jamulus 3.9.1 适配笔记（OHOS PC aarch64）

## 概览

- 上游: https://github.com/jamulussoftware/jamulus (tag r3_9_1)
- 构建: qmake（Qt5），`CONFIG+=serveronly CONFIG+=headless`
- 产物: `bin/jamulus`（无 GUI 服务器二进制；客户端 GUI/JACK 音频后端整体不参与编译）
- 依赖: qt/5.15.19（制品仓已发布）；opus 为上游 vendored 源码（libs/opus），无外部依赖

## 适配决策

### serveronly + headless 构建目标

jamulus 是客户端-服务器架构：客户端需 JACK/ALSA/ASIO 音频后端与 Qt5Widgets，
服务器（jamulus -s）仅需 Qt5Network/Xml/Concurrent + vendored opus。OHOS 设备无
JACK 守护进程，`serveronly`（SERVER_ONLY 宏，裁掉 src/sound/* 全部音频后端）+
`headless`（HEADLESS 宏，QT -= gui，INSTALLS 仅 target）是平台正确的交付形态。
产物仍可运行 `--version`/`--help` 与服务器模式（`jamulus -s`）。

### lrelease 未构成阻塞（实测结论）

制品仓 qt/5.15.19 包 bin/ 确实未随附 lrelease 宿主工具（全缓存实测：所有 qt*
包 bin 均 0 个 lrelease）。`CONFIG += lrelease` 的 lrelease.prf 在本配置下
（qmake 交叉 profile + 预生成 .qm 先于构建存在）未对缺失的 lrelease 二进制
构成硬失败——conan create 全程无 lrelease 调用错误。**最终配方不带任何补丁**
（patches: {}），与 W3 实测通过的形态完全一致（R-truth：只发布实测过的东西）。
build() 预生成合法空 .qm（Qt5 qm 头 v3，0 context/0 message）——
src/resources.qrc 以 `<file alias>` 嵌入 13 个 src/translation/*.qm，
rcc 要求文件存在；空翻译被 QTranslator::load() 接受，界面回退英文
（上游主语言）。knowthelist/2.3.1 同方案先例。

### qmake 交叉编译要点（沿用 knowthelist/2.3.1 已验证结论）

- qmake 探测编译器走 PATH 解析、不读 CC/CXX → run 命令内联
  `PATH=<qt_pkg>/bin:/data/service/hnp/bin:$PATH` 前缀（部分 worker 的
  Environment().vars().apply() 注入不可靠，PR #11153 实证）。
- build() 用 `Environment().vars(self).apply()` 上下文，不用 save_script("conanbuild")
  （自引用无限递归 → qmake SIGSEGV）。
- make install 用 `STRIP=true` 覆盖 strip（HMDFS 上 strip 后 ELF 不可执行，
  acetoneiso/knowthelist 同款坑）。
- serveronly 分支无 PKGCONFIG 需求，无需 PkgConfigDeps/qmake pkg-config 处理。

### opus vendored 源码

Jamulus.pro 按 QT_ARCH 选择 opus 架构分支（arm64-v8a → NEON intrinsics 源码，
armcpu/arm_celt_map 等 .c 文件，clang aarch64 可编译）。若 QT_ARCH 不匹配
（如非 arm64-v8a），回落通用 C 路径，同样可编译。W3 实测结果见下。

## 上游测试清点（R51 申报表）

- 上游 r3_9_1 源码树无 tests/ 目录；Jamulus.pro 仅定义 build/install/clang_format
  目标，无 make check / ctest / pytest；tools/ 为发行维护脚本（changelog-helper 等）。
- 结论：**上游确无自动化测试**，test_package 提供消费者视角冒烟测试
  （`jamulus --version` 走 main.cpp:158 真实参数解析，断言 exit 0 + 输出含 3.9.1）。

## W3 实测记录（2026-10-13）

- `conan create`（ohos-aarch64 profile，qt/5.15.19 binary 从制品仓下载）：
  **PASS**。qmake CONFIG+=serveronly headless 编译全程无错误；vendored opus
  按编译器原生 aarch64 路径编译，未触发 .pro 的 QT_ARCH 分支问题。
- test_package 冒烟测试（conan-create.log L550-589）：`jamulus --version`
  exit 0，输出 "*** Jamulus, Version 3.9.1" → 断言通过。
- conan-verify 门禁：G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS
  （reports/conan-verify-report.md，verdict PASS）。
- 环境备注（本机特有，非配方内容）：源码经 backup-sources 离线喂入——conan 2.29.1
  要求 backup 基址同时提供 `<base>/<sha256>` 与 `<base>/<sha256>.json` 元数据
  （缺 .json 即 NotFoundException），file:// scheme 不被支持
  （"No connection adapters"）。
---

**编译结束**: 2026-10-13 23:38
**最终状态**: published
