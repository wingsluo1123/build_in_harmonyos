# bdf2sfd 1.1.9 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt`，`cmake_minimum_required(VERSION 3.10)`，C99）
- 编译日期: 2026-10-07
- 编译器: clang 15 / clang++（OHOS profile `ci/conan/profiles/ohos-aarch64`，`os=OHOS`、`arch=armv8`）
- 状态: built

## 货源（权威，勿改）

| 项 | 值 |
|---|---|
| 官方直链 | `https://codeload.github.com/fcambus/bdf2sfd/tar.gz/refs/tags/1.1.9` |
| sha256 | `d7638e55cf80eb475668dcf062d767b00d3b2d577156f39e7911966b8b711bd6` |
| 字节数 | 20489（本机 `curl -fsSL` + `sha256sum` 实测，与 tag `1.1.9` 逐字对应） |

⛔ 不得把 Debian 池址当货源（PF7 拉黑 `deb.debian.org`）。

## 编译步骤

1. `conan create` 干净构建（G2）：`source()` 下载 → `cmake.configure()` → `cmake.build()` → **`cmake.test()` 跑上游 ctest 5 项** → `cmake.install()`。
2. 上游 `CMakeLists.txt` 的条件分支实测：
   - `check_function_exists(pledge HAVE_PLEDGE)` → **not found** ⇒ 自动编入 `compat/pledge.c`
   - `check_function_exists(strtonum HAVE_STRTONUM)` → **not found** ⇒ 自动编入 `compat/strtonum.c`
   - `ENABLE_SECCOMP` 默认 `0`（上游标 experimental、按架构选定）⇒ 配方 `tc.cache_variables["ENABLE_SECCOMP"] = "0"` 固定关闭，行为与上游 CI 一致
3. 产物：`bin/bdf2sfd`（可执行）+ `share/man/man1/bdf2sfd.1`。

## 测试数（五维账本，`手册/04 §10.1`；与 manifest / test_package/MANIFEST.yml 三处同源）

| 维度 | 数值 | 来源 |
|---|---|---|
| `N_static`（上游静态声明） | **5** | `CMakeLists.txt:65-70` `enable_testing()` + 5 个 `add_test` |
| `N_registered`（构建系统注册） | **5** | `ctest -N` 实测 `Total Tests: 5` |
| `N_executed`（实际执行） | **5** | `ctest` 实测 `100% tests passed, 0 tests failed out of 5`（0.30s） |
| 未执行分类数 | **0** | 无跳过、无预期失败、无条件注册 |
| `N_consumer`（新增消费者测试） | **1** | `test_package/test.sh`，含 **5 项断言**，实测 `5/5 checks PASS` |

**上游表合计 = `N_static` = 5；适配后合计 = 5（上游）+ 1（消费者）= 6。**

按 `§12.72` 四类实测自数（2026-10-07，源码 tag 1.1.9 就地清点）：

| 类别 | 实测 | 说明 |
|---|---|---|
| `test*/` 框架源码 | **0** | `tests/` 下无 `.c` 测试框架源码 |
| `*/res` 语料 | **4** | `tests/spleen-{8x16,12x24,16x32,32x64}.bdf` |
| `**/*RUNTEST*` 脚本 | **0** | 全树无此类文件 |
| `src/demo\|examples/*.c` 示例 | **0** | 无 `demo/`、无 `examples/` |

> 语料 4 是 4 项转换测试的输入，另 1 项是无参调用 ⇒ 语料数(4) + 无参(1) = ctest 注册 5，两口径自洽。
> 注册口径：`ctest -N` = 5（`bdf2sfd` / `8x16` / `12x24` / `16x32` / `32x64`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 首条真实错误 `Error in source() method, line 41` → `BadZipFile: File is not a zip file` | 官方直链末段是 `refs/tags/1.1.9`、**无压缩扩展名**，conan `get()` 推断不出格式、按 zip 解包 | 在 `conandata.yml` 的 `sources` 显式加 `filename: "bdf2sfd-1.1.9.tar.gz"`（仓库既有惯例：`abbtr/1.0.4`、`acf-alpine-conf/0.9.1` 等同款），`get(**self.conan_data["sources"])` 自动带入 |
| 2 | test_package 断言 `FAIL: -f not applied` | 断言里给 `-f`/`-p` 的取值多加了引号；实测（`cat -A` 逐字节）上游是**原样输出、不加引号**：`FullName: HarmonyMinimal`、`FontName: Harmony-Minimal` | 改断言为无引号形态（本地先复现→先本地验绿→再烧构建轮次） |
| 3 | 模板 `package_type="library"` + `cpp_info.libs=["bdf2sfd"]` + `license="MIT"` | conan-init 的 cmake 模板默认按库生成 | 按 CLI 工具改：`package_type="application"`、`cpp_info.bindirs=["bin"]`、`license="BSD-2-Clause"`（上游 `LICENSE`/`CMakeLists.txt` SPDX）、补 `homepage`/`url`，并建软件级 `commands.json`（R38/PF8） |
| 4 | conan-init 生成的 `test_package/test.c` 只 `printf` | 空壳测试，会被 PF3/R34 拦 | 删 `CMakeLists.txt`/`test.c` 脚手架，改 `test.sh` 实际调用已安装 `bdf2sfd` 二进制做端到端转换断言 |

## 源码修改

**无补丁**（`patches/` 为空）。上游代码在 OHOS 上零修改即可构建与运行；`compat/` 是上游自带的可移植性 shim，不是我们的补丁。

## 依赖版本

**无外部依赖**（libc 级闭合）。证据：
- 上游 README `## Dependencies`：*"bdf2sfd uses the `CMake build system and does not requires any external dependencies."*
- 本机 grep 实测：全树 `find_package` / `pkg_check_modules` / `AC_CHECK_LIB` / `target_link_libraries` **命中 0**
- `W0 preflight_check.sh bdf2sfd/1.1.9` → `[OK] 预检通过（无依赖需要检查）`（conanfile 尚无依赖声明）

## 验证结果

```bash
# 1) 上游 ctest（本地，R51）
$ ctest
100% tests passed, 0 tests failed out of 5
Total Test time (real) =   0.30 sec

# 2) conan-verify 8 道门禁（G0/G1/G2/G3/G4/L2/L4/L5）
$ ohc-run.py conan-verify bdf2sfd 1.1.9
✅ 配方验证通过: bdf2sfd 1.1.9   # VERIFY_RC=0
#   脚注（W4B-2 披露）：本命令的明细里 G4 = 「⚠️ 无法找到程序包 ID」，L2/L4/L5 = 「⏭️ 跳过（无 cache 路径）」—— 工具虽在各段标 ✅ PASS，但这两类明细不是实质检查通过。
#   可接受性：G4 需 conan cache 路径解析 package ID、本地无该路径故降级；L2/L4/L5 无 cache 时按工具既有行为跳过；上行「8 道门禁 PASS」的实质依据是 G0/G1/G2/G3（G2 = conan create 真跑），产物面以 reports/ 手工读数为准（明细见 reports/conan-verify-report.md:39/42/45/48）。

# 3) 消费者测试（conan create 内 test_package）
--- bdf2sfd consumer verification ---
PASS 1: -v -> bdf2sfd 1.1.9
PASS 2: -h usage rendered
PASS 3: no-arg invocation rc=0 (no crash)
PASS 4a: SFD magic SplineFontDB: 3.0
PASS 4b: -f applied to FullName
PASS 4c: -p applied to FontName
PASS 5: 2 glyphs converted
test bdf2sfd 1.1.9: 5/5 checks PASS

# 4) 版本逐字一致
$ ./bdf2sfd -v
bdf2sfd 1.1.9
```

通过率口径：**上游执行项 5/5；静态全量 5/5；消费者断言 5/5。**

## 适配面（B=none 的支撑读数）

- **设备面 = 无**：全树 `dlopen`/`dlfcn`/`pthread`/`socket(`/`fork(`/`shm_`/`mmap`/`sysconf`/`/proc/` **命中 0**；仅 `seccomp` 有命中（`src/bdf2sfd.c:29,30,92,97` + `src/seccomp.h`），但 `ENABLE_SECCOMP` **默认 0 且本配方固定关闭** ⇒ 默认构建不含 seccomp，不构成设备能力缺口。
- **语言**：c/cpp 实测 **14 个源文件**（`src/` 9 + `compat/` 5），脚本 0 ⇒ 与任务声明一致（c↔cpp 兼容族）。
- 知识图谱检索：`bdf2sfd` 在 `knowledge/graph/index.tsv` 无专属条目；font 域最近条目 `E305` 是**字体资源型数据包**（`build()` 为空、装 `.otf`），与本包"CMake 构建的转换器工具"机制不同，不适用。

## 注意事项

- `ENABLE_SECCOMP` 保持 `0`：上游标注 experimental 且按架构选定，打开会引入 `linux/seccomp.h` 依赖面，与"零依赖"定位冲突。
- SFD 输出到 **stdout**，glyph 进度打到 **stderr**（`Processed N glyphs in ...`），消费方测试需分开捕获。
- OHOS 上 `/system/bin/sh`（mksh）不能直接执行 ELF ⇒ `test_package` 用 bash wrap（`CONFIG_SHELL` 或 `/data/service/hnp/bin/bash`），并按 `§12.73③` 种子 `PWD`。
---

**编译结束**: 2026-10-07 22:00
**最终状态**: built
