# qabc 1.16 适配笔记（HarmonyOS PC / arm64）

## 软件概览

qabc 是 ABC 乐谱最小 GUI（Qt6 Widgets，qmake 工程）：提供 ABC 乐谱文本编辑、
MIDI/AUDIO/PostScript 生成（依赖运行时外部工具 abc2midi/abcm2ps/fluidsynth/
zathura，可选功能，缺省时退化为纯文本编辑器）。上游 1.16 为 qmake 工程
（qabc.pro，QT += core widgets gui），GPL-3.0-or-later。

- 上游：https://github.com/be1/qabc （tag 1.16）
- 源码 sha256：`c5b9397b84c755a87871259f2b1fa5610d619eeb39a80ccec8c0bc26aee41086`

## 适配决策（W0/W0b 核验）

1. **依赖链已发布**（conan download/list 实测）：qtbase/6.11.1 ✅、
   qttools/6.11.1 ✅（qttools 提供 lrelease 翻译编译工具，qtbase 包内
   无 LinguistTools）。独立可做，无需先发依赖。
2. **上游无测试用例**：源码树无 tests/ 目录、无 make check 目标、无测试
   注册项（GitHub 仓库树核验），N=0。test_package 自研冒烟测试
   （--version/--help，offscreen 平台）补充，见下。
3. **构建系统**：qmake 工程（非 autotools/cmake），配方 build() 直接调用
   qtbase 包内 qmake6 + make。

## 平台差异诊断与修复

| # | 断裂点 | 修复 |
|---|--------|------|
| 1 | qmake6 生成的 Makefile 中 lrelease 路径为 `$$[QT_INSTALL_BINS]/lrelease`，qtbase 包内无 lrelease（在 qttools 包） | 配方 build() 传 `QMAKE_LRELEASE=<qttools>/bin/lrelease` 覆盖 |
| 2 | qtbase/qttools 的 host 工具（qmake6/lrelease/moc）是 OHOS 本机 ELF，DT_NEEDED 含 libc++_shared.so，仅 OHOS SDK `llvm/lib/aarch64-linux-ohos/` 提供 | generate() 中把 SDK libc++ 目录与 qtbase/qttools lib 注入 LD_LIBRARY_PATH（fingerterm 同款） |
| 3 | test 阶段运行 qabc 二进制同样缺 libc++_shared.so 与 Qt6 动态库 | test_package 的 test() 同样注入 SDK libc++ 目录与依赖包 lib（fingerterm test_package 同款） |
| 4 | 纯可执行包（GUI，无 lib/ 产物） | package_type=application；package_info 不声明 cpp_info.libs（kapow 先例）；构建产物直接复制未 strip 的 ELF（OHOS hmdfs 上 strip 后无法执行） |

## 依赖版本

- qtbase/6.11.1（Core/Gui/Widgets）
- qttools/6.11.1（lrelease 翻译工具）

## 上游测试清点（R51 申报表）

清点口径：官方 1.16 源码树（GitHub `be1/qabc` tag 1.16 tarball 全文件清单）+
构建系统（qabc.pro）+ GitHub 仓库树。**无 tests/ 目录、无 ctest / pytest /
make check 测试注册项**，上游自动化测试数量为 **0（N=0）**。

| 测试项 | 依赖 | 状态 |
|---|---|---|
| （上游无自动化测试用例） | — | N=0（附清点证据） |

自研补充（test_package，上游 N=0 时补全）：

| 测试项 | 依赖 | 状态 |
|---|---|---|
| `qabc --version` 版本串断言（test.sh） | 包内二进制 + qtbase | ✅ 实测通过 |
| `qabc --help` 帮助文本断言（test.sh） | 包内二进制 + qtbase | ✅ 实测通过 |
| `test_render` offscreen 渲染快照自检（test_render.cpp） | 包内二进制 + qtbase(Widgets) | ✅ 实测通过 |

- 测试数量：上游 0 + 自研 3 断言 = **3**，通过率 **3/3（100%）**
- 环境（environment）：OHOS（HarmonyOS PC）aarch64/armv8
- profile：ohos-aarch64（ci/conan/profiles/ohos-aarch64）
- 运行方式：`conan create archives/q/qabc/1.16 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
  （test_package 内 `QT_QPA_PLATFORM=offscreen`）

## 验证结果

```bash
# offscreen 平台（OHOS 无显示服务器）
QT_QPA_PLATFORM=offscreen ./qabc --version   # → "QAbc 1.16 (stable)" exit 0
QT_QPA_PLATFORM=offscreen ./qabc --help      # → usage 正常 exit 0
# conan-verify：G1-G4 全部 PASS
```

test_package 自研 3 项断言（上游 N=0）：
1. `--version` 版本串断言（test.sh）
2. `--help` 帮助文本断言（test.sh）
3. Qt6 Widgets offscreen 渲染快照自检（test_render.cpp：创建
   QWidget+QLabel 并 grab 渲染一帧，校验图像尺寸非零）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Qt6 qmake 构建配方（qtbase+qttools 依赖、SDK libc++ 注入） |
| conandata.yml | 上游源码 URL + sha256 |
| test_package/ | 冒烟测试（--version/--help 断言） |
| commands.json | 纯可执行包命令声明（R38） |

## 注意事项

- 运行时外部工具（abc2midi/abcm2ps/fluidsynth/zathura）为可选功能，
  README 声明缺省时退化为纯文本编辑器；OHOS 上未适配这些 BIN 工具，
  不影响编译与主界面功能。
- 翻译 .qm 文件构建产物在源码树 locale/ 下，package() 复制到
  share/qabc/locale/。
---

**编译结束**: 2026-10-15 21:52
**最终状态**: built
