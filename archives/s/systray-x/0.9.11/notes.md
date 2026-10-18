# systray-x 0.9.11 适配笔记

## 编译环境
- 构建系统: qmake（Qt5 项目，.pro/.pri 文件）
- 编译日期: 2026-10-18
- 编译器: clang 15.0.4（OHOS aarch64 profile）
- 状态: built

## 编译步骤

1. init-build: 下载官方 GitHub 标签归档 0.9.11（SHA-256 1aebd2ad17ec5b05aff0b680257f170729ebaa57db2ba1de6c1687e9291be7f8）
2. lang-preflight: detected=qmake/qt，任务语言 cpp 兼容族，通过
3. 探索性编译: qmake + make → 生成 SysTray-X 可执行文件
4. conanfile.py 编写: application 型配方（Qt5 qmake 构建）
5. 适配修改:
   - 移除 QX11Info → 用 XOpenDisplay 替代（消除 Qt5X11Extras 依赖）
   - 禁用 KDE 集成（OHOS 无 KNotifications）
   - 修复 .pro 文件中的 -L 路径（ld.lld 不读取 LIBRARY_PATH）
   - 修复 .pri 文件中的 git 版本检测（源码 tarball 无 git）
6. conan create 通过，test_package 包含鸿蒙特有测试

## 适配要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `QX11Info` 不可用 | Qt5X11Extras 模块在 qt 包中不可用 | 替换为 `XOpenDisplay(NULL)` |
| 2 | `KStatusNotifierItem` 头文件缺失 | OHOS 无 KDE Frameworks | 启用 `NO_KDE_INTEGRATION` 宏 |
| 3 | `ld.lld: unable to find library -lX11` | ld.lld 不读取 LIBRARY_PATH 环境变量 | 通过 `replace_in_file` 在 .pro 文件中注入 `-L` 路径 |
| 4 | `X11/X.h` 头文件找不到 | xorgproto 的 include 路径未传递给 qmake | 在 .pro 文件中注入 `QMAKE_INCDIR` |
| 5 | git 版本字符串解析失败 | 源码 tarball 无 git 仓库 | 硬编码版本字符串常量 |
| 6 | test_package 缺少鸿蒙特有测试 | rule12 要求至少一个鸿蒙特有非断言测试 | 添加 ELF NEEDED 验证脚本 |

## 依赖版本

- qt/5.15.19.1（OHOS 适配版）
- libx11/1.8.13.1
- libxcb/1.17.0.1
- xorgproto/2025.1

## 验证结果

```bash
# conan create 构建
PASS: SysTray-X binary present
PASS: OHOS closure test (ELF magic + NEEDED entries)

# test_package 测试
- SysTray-X 二进制存在性检查通过
- 鸿蒙特有 ELF NEEDED 验证通过（libX11.so 在 closure 中）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 型配方（Qt5 qmake + OHOS 适配） |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/ | 消费者测试 + 鸿蒙特有测试 |
| test_ohos_closure.py | 鸿蒙特有 ELF NEEDED 验证 |
| manifest.yaml | 版本级元数据 |
| notes.md | 本文档 |

## 对话记录

### 对话 #1 — 2026-10-17/18 适配与排错

- 目标：在 OHOS PC（aarch64, clang 15, libc++）上以 Conan 方式编译 systray-x 0.9.11，依赖全部走 `conan download` 预置，不使用 `--build=missing` 绕过。
- 依赖解析：qt/5.15.19.1（提供 qmake 与 `harmonyos-clang` mkspec）、libx11/1.8.13.1、libxcb/1.17.0.1、xorgproto/2025.1。
- 排错 1：源码中 `#include <QX11Info>` 失败，qt 包未提供 Qt5X11Extras。改为 `XOpenDisplay(NULL)`，同时从 `.pro` 移除 `QT += x11extras`。
- 排错 2：`KStatusNotifierItem` 头文件缺失（无 KDE Frameworks）。在 `.pro` 中启用 `DEFINES += NO_KDE_INTEGRATION`。
- 排错 3：编译期 `X11/Xlib.h`、`X11/X.h` 找不到。把 libx11 / libxcb / xorgproto 的 include 目录通过 `QMAKE_INCDIR` 注入 `.pro`。
- 排错 4：链接期 `ld.lld: error: unable to find library -lX11`。`LIBRARY_PATH` 对 ld.lld 无效，改为在 `.pro` 中注入 `LIBS += -L<libx11>/lib -L<libxcb>/lib`。
- 排错 5：源码 tarball 无 `.git`，`.pri` 的 `git describe` 版本探测为空。以固定 `0.9.11` 版本串替换。
- 校验：`conan create` 全量重编译通过；产物 `bin/SysTray-X` 为 723,584 字节 aarch64 ELF。
- 鸿蒙特有测试：`test_ohos_closure.py` 用纯 Python 解析 ELF64 动态段（不依赖 readelf），实测 `DT_NEEDED` 为 `libX11.so.6`、`libQt5Widgets.so.5`、`libQt5Gui.so.5`、`libQt5Core.so.5`、`libc++_shared.so`、`libc.so`，为报告式非断言检查。
- 审计修正：归档目录曾混入 `src/`（8.6MB 上游源码，含 6MB `ghr` 二进制）与未被引用的 `patches/`，已移除；`conandata.yml` 一度被误写为他包内容，已恢复为官方 URL 与 SHA-256（`1aebd2ad...be7f8`，与重新下载的 tarball 校验一致）。

## 注意事项

- Qt5 的 qmake 构建系统通过 .pro 文件传递 -L/-I 路径，不要用环境变量
- OHOS 的 ld.lld 不读取 LIBRARY_PATH，必须通过命令行参数传递库路径
- systray-x 是 Thunderbird 扩展原生应用，无上游自动化测试套件
- 积分赛任务：不提交知识草稿文件，但 manifest 保留 knowledge_gained 字段
---

**编译结束**: 2026-10-18 04:19
**最终状态**: built
