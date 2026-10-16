# yorick 2.2.04 适配笔记（OHOS/aarch64 原生 build=host）

## 编译环境
- 构建系统: 自定义 `configure`（sh 脚本，非 autoconf）+ 手写 Makefile
- 编译日期: 2026-10-15
- 编译器: clang 15（`/data/service/hnp/bin/clang`），原生构建（build = target = OHOS/aarch64，铁律 #0：未使用 `--host/--build/--target`）
- Conan: 2.29.1；profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（conan create + conan-verify；未 upload）

## 编译步骤

```sh
NO_XLIB=1 CC=/data/service/hnp/bin/clang sh ./configure   # 生成 Make.cfg / play/unix/config.h
NO_XLIB=1 make -j1                                        # 解释器 + gist + 静态库 libyor.a
./yorick -batch ../ohos-headless-check.i                  # 上游解释器/数值测试（见下）
```

- yorick 无任何必需外部依赖（ANSI C + POSIX）；X11 为可选，本适配显式 `NO_XLIB=1` 关闭。
- `CC` 从 Conan conf `tools.build:compiler_executables` 取值，经 `generate()` 写入 `conanbuild` 环境脚本（R33）；脚本名用 `yorick_build`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 在 `sh ./configure` 处直接 `Error -11`（SIGSEGV），无任何 configure 输出 | `generate()` 里 `env.vars(self).save_script("conanbuild")` 与 Conan 自动生成的聚合脚本 `conanbuild.sh` **同名**，生成自引用脚本 `. conanbuild.sh && . conanbuildenv-...`，加载时无限递归致 sh 段错误 | 改用唯一脚本名 `save_script("yorick_build")`。**已知坑**（见 knowledge/drafts/DRAFT-cd-hit-4.8.1-make-conan-recipe.md），本次复用 |
| 2 | `make check` 在 `lissajous`/`testg` 处 `ERROR: No interactive graphics in this Yorick -- hcp only` | 上游 `i/testfull.i` 含交互图形测试（`window`），NO_XLIB 构建无 X11 后端（`yorick/graph.c` 在 `-DNO_XLIB` 下对显示请求硬报错） | 交互图形测试在本平台**不可运行**（无 display，libx11 未发布）。build() 改为驱动同一批上游脚本中的解释器/数值项；图形项 NOT_RUN 如实记录（见下） |
| 3 | 打包后 `bin/yorick` 需在 `bin/../i0` 找到解释器运行时 | yorick 以可执行文件父目录定位 `i0/std.i`（relocatable 布局） | package() 保持上游 relocate 布局：`bin/` 与 `i0/ i/ i-start/ g/ lib/ include/` 同级 |

## 源码修改

无。本次未生成 source patch（`patches: {}`）。上游 x11 后端通过 `NO_XLIB=1` 编译开关关闭，无需改动源码。

## 依赖版本

无外部 Conan 依赖（仅 ANSI C / POSIX / libm）。

## 验证结果

### 上游测试（R51；单位 = `i/testfull.i` 中的一次顶层调用）

**TOTAL = 9 = PASS 3 + FAIL 0 + SKIP 0 + NOT_RUN 6**

| # | 上游项 | 结果 |
|---|--------|------|
| 1 | `#include "testp.i"`（解析器 + 字符串 + oxy 编译器 + 二进制/ASCII/netCDF I/O + 3 项计时子测） | **PASS**（parser `0 goofs`、string `0 goofs`、8 项 oxy `PASSED`；9 个 I/O 阶段；Shock tracker / Escape factor / Zone generator 计时通过） |
| 2 | `testm`（数学库） | **PASS** |
| 3 | `testlp, 200`（LINPACK 基准） | **PASS** |
| 4 | `lissajous, 0` | NOT_RUN（需交互图形设备） |
| 5 | `lissajous, 1` | NOT_RUN（同上） |
| 6 | `testg`（grbench 图形基准） | NOT_RUN（同上） |
| 7 | `demo2`（图形/网格演示，window + palette） | NOT_RUN（同上） |
| 8 | `grtest, quick=1`（24 帧综合图形） | NOT_RUN（同上） |
| 9 | `txtest, quick=1`（9 帧文本/排版） | NOT_RUN（同上） |

NOT_RUN 原因（能力缺项，非跳过）：本机为 `-DNO_XLIB` 无头构建 —— 无 X11 后端、无 X server，`libx11` 也未发布到 ohpcd；上游图形测试调用 `window`/`palette`，需要交互显示或 hcp 图形设备。`yorick/graph.c` 在 `-DNO_XLIB` 下对显示请求报 `No interactive graphics in this Yorick -- hcp only`（未改源码、未删用例、未改断言）。

### 消费者测试（test_package，调用已安装二进制）

- `test.i`：11 条真实断言（标量算术 / `sum`,`max`,`min`,`anyof` 规约 / 列主序矩阵索引 / FFT 正反变换往返），任一不符即 `error` 中止。
- `test.sh`：断言退出码 0 且输出含 `YORICK_CONSUMER_OK`。
- 结果：**PASS 1/1**（`YORICK_CONSUMER_OK`）。另从包布局任意 cwd 直接运行 `bin/yorick -batch test.i` 亦 PASS（可重定位验证）。

### 门禁

- `conan create`（profile ohos-aarch64，`--build=yorick/*`）：**exit 0**（build + smoke + test_package 全过）。
- `conan-verify`：见 receipts 回执（逐项）。
- CI 同构 `ci/conan/build_and_test.sh`：见 receipts 回执。

## 注意事项

- 上游测试套件对无显示环境不友好：`make check` 在有 X11/headless 上会于首个交互图形用例中止；图形子集在无头构建下不可运行，已在 MANIFEST.yml 如实分栏。
- 大坑（跨库）：`save_script("conanbuild")` 与 Conan 聚合脚本同名 → 自引用 → SIGSEGV；务必用包私有名字。
