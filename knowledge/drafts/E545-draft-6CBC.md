# E545 — 手写 Makefile 写死字面量 g++ 与 -march=k8，CXX 环境变量无效

## 错误特征

- OHOS clang 编译 `-march=k8`：`clang-15: error: unsupported argument 'k8' to option '-march='`（实测）。
- 原始 Makefile 即使传入 `CXX=/data/service/hnp/bin/clang++`（环境变量和命令行都试过），`make -n` 仍是 `g++ -DVERSION=... -c -o prefix_tree.o ...`。
- 构建机恰有宿主 `g++` 时静默产出 x86 目标文件，链接交叉编译的 `libpopt.a` 报
  `skipping incompatible .../libpopt.a`、`cannot find -lpopt`（实测）；没有 `g++` 时则是 `g++: not found`。

## 触发条件

- 构建系统: 手写 Makefile（无 configure/CMake）
- 阶段: make（编译/链接）
- 特征: 规则命令里直接写 `g++ ...`，编译选项用 `CPPFLAGS += ... -march=k8` 追加

## 根因分析

patman 1.2.2 的 Makefile 把 `g++` 当字面量写在链接规则和 `%.o` 规则的命令行中，而不是 `$(CXX)`。
因此 Conan `AutotoolsToolchain` 注入的 `CXX`、或 `make CXX=...` 都改变不了实际调用的编译器。
`CPPFLAGS +=` 会与环境变量合并，`-march=k8` 是 x86 专有参数，没法通过环境变量剔除，只能改文件或在命令行整体覆盖 `CPPFLAGS=`。

## 解决方案

### 推荐方案

用补丁（`refresh-patch --auto` 生成）把规则里的 `g++` 改成 `$(CXX)`，删除 `-march=k8`（本包同时把 `version := 1.2` 改为 `1.2.2`）。
配方 `generate()` 用 `AutotoolsToolchain` + `AutotoolsDeps` 注入 CXX 与 popt 的 `-I/-L`，`build()` 在源码目录执行
`self.run("make patman", cwd=self.source_folder)`；`package()` 直接复制产物，避开上游 `install -s`（会用构建机 strip 处理 aarch64 ELF）。

### 禁止做法

- ❌ 保留 `-march=k8` / 改成 `-march=native`：把构建机架构带进交叉构建。
- ❌ 把 `clang++` 软链成 `g++`，或设 `CXX=g++`：掩盖编译器选择问题。

## 验证

```bash
grep -nE '^[[:space:]]+(g\+\+|gcc|cc) |-march=' Makefile
make -n CXX=/data/service/hnp/bin/clang++ | head -3      # 仍显示 g++ 即为字面量
conan create archives/p/patman/1.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 关联条目

- 相近（草稿池）：cohomcalg-0.32-makefile-gxx-override（变量 `CC := g++`，命令行覆盖）、jnoise-0.6.0-makefile-linkline-literal-cxx-name（链接行字面量）、genann-1.1.1-make-cflags-march-native-override（`-march=native`）。本条目的差异：规则命令字面量 g++ 无法被覆盖 + `-march=k8` 在 OHOS clang 的确切报错 + 宿主 g++ 静默混链的现象与取证。
- 正式库最相近：E053（cc1plus），相似度 0.12。
