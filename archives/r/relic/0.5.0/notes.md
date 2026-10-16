# relic 0.5.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，hnp 工具链）
- CMake: 4.1.2 / Conan: 2.29.1 / 归档 profile: `ci/conan/profiles/ohos-aarch64`
- 状态: built（`conan-verify` G0–G4 + L2/L4/L5 全 PASS）

## 编译步骤

1. 取源：官方 tag 归档 `codeload.github.com/relic-toolkit/relic/tar.gz/refs/tags/relic-toolkit-0.5.0`
   （HTTP 200 / 645936 B / sha256 `e6b34be22a5534382b7d7f9bf1bcb6b9691bb037e14f71b33dac076629c60f71`，
   解包根目录 `relic-relic-toolkit-0.5.0` ⇒ `strip_root`）。URL 末段没有 `.tar.gz` 后缀，
   故 conandata 显式给 `filename: relic-0.5.0.tar.gz` —— 否则 conan 按 URL 落盘成无扩展名文件，
   `get()` 的解包器回落到 zipfile，报 `BadZipFile: File is not a zip file`（本次实测撞过一次）。
2. 配方 `generate()` 注入 cache 变量（全部落在配方层，**上游源码零修改、0 补丁**）：
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`、`OPSYS=LINUX`、`TESTS=1`、`BENCH=0`、`DOCUM=OFF`，
   并按 `shared` 选项配平 `SHLIB`/`STLIB` 互斥开关。
3. 官方验证链：
   `preflight_check.sh relic/0.5.0` → `recipe-search relic` → `build relic 0.5.0`
   → `conan-verify relic 0.5.0`（内部即干净 `conan create`，含 18 项 ctest 与 test_package）
   → `finish relic 0.5.0 built`（W2 结构 + W3 本地 CI 模拟）。
4. 设备命令形如：
   `conan create <归档目录> -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<同上> --build=missing --user=ohpcd --channel=stable`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed` | 上游首行 `cmake_minimum_required(VERSION 3.1)`，设备 CMake 4.1.2 已移除 <3.5 兼容 | 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`；**必须走 `tc.cache_variables`（= 命令行 -D，先于任何 CMakeLists 解析）**，写进 `tc.variables` 会落在首行之后不生效（该机制知识库已收录：E187 `add-cmake-flag` / E103 `bump-cmake-minimum-version`，本包判 `hit`） |
| 2 | configure 打出 `-- Configured operating system: `（**空**），`TIMER:STRING=ANSI`，全构建树 **0/36** 处 `_GNU_SOURCE`，链接行无 `-lrt` —— 但**退出码 0、18/18 测试照常全绿** | `CMAKE_SYSTEM_NAME=HarmonyOS`（OHOS profile 映射 + 设备 `uname -s` 即 HarmonyOS），上游 `CMakeLists.txt:183 if(CMAKE_SYSTEM_NAME STREQUAL Linux)` 不命中 ⇒ 派生 cache 变量 `OPSYS` 留空 ⇒ `:194` 的 `-D_GNU_SOURCE`、`:199` 的 `TIMER=HPROC`、`src/CMakeLists.txt:172` 的 `-lrt` 三处下游分支**同时静默退化** | 配方注入 `tc.cache_variables["OPSYS"]="LINUX"`：上游 `set(... CACHE STRING ...)` 无 `FORCE` 不覆盖已有 cache 项，且该 `set()` 在 `if()` 之前执行 ⇒ **一行注入同时恢复三处**（A/B 实测见验证结果）。同族既有条目 E140/E267/E543/E607/DRAFT-openxr 的解法都是「改分支条件 / 补 package_info」，本条走配方层零补丁路径 ⇒ 判 `create`，草稿 `knowledge/drafts/DRAFT-relic-0.5.0-harmonyos-linux-branch-opsys-injection.{kv,md}` |
| 3 | `-DARITH=arm-asm-254` 配置后**编译即失败**：`error: invalid operand`，源文件含 `MOV pc, lr`、`LDMIA sp!, {r4-r12, r14}` | 那些 `.s` 是 **AArch32（32 位 ARM）** 指令，本目标是 aarch64；`src/low` 下 94 个 `.s` 分属 arm32/x86/avr/msp 后端，本目标**无一可用** | 用上游默认 `ARITH=easy`（可移植 C 后端）。本包**不申报**「含汇编的复杂架构」类资质 —— 汇编后端在本目标未被行使 |
| 4 | 上游默认 `TESTS=100` / `BENCH=100`（每条用例跑 100 遍）会把构建时间顶爆 | 上游把用例重复次数做成 cache 变量，面向基准测试场景 | `TESTS=1`（每条跑一遍）+ `BENCH=0` + `DOCUM=OFF`（后两者不进包）；ctest 带 `--timeout 1800`，失败时先把 `Testing/Temporary/LastTest.log` 尾部打出再抛，不吞错误 |
| 5 | 构建驱动 Step7 `make check` 报 `No rule to make target 'check'` | relic 用 **ctest** 注册测试（`test/CMakeLists.txt` 的 `ADD_MODULE` 展开 `add_test`），上游**没有** `check` 目标 | 不改上游；真实测试由配方 `build()` 内 `cmake.ctest()` 执行（18/18 全过）。`reports/test-report.md` 中的 `Status: FAIL RC: 2` 是该驱动步骤的产物、非测试失败，判定以 `reports/conan-create.log` 的 ctest 汇总行为准 |
| 6 | 构建日志出现 `make: jobserver mkfifo: ... Operation not permitted`（warning） | HMDFS 不允许在该路径 mkfifo | 不影响构建与退出码，仅丢失 make jobserver 并行，不处理 |
| 7 | `conan-verify` G2 首次失败：`Error in source() method … BadZipFile: File is not a zip file` | 构建驱动 Step9 的 `conan-init` 用模板**覆盖了手写 `conanfile.py` 与 `conandata.yml`**（模板 conandata 没有 `filename` 键）⇒ 落盘名无扩展名 ⇒ 解包器选错 | 从备份恢复手写配方后**直接跑 `conan-verify`**，不重跑 `build`（Step9 会再次覆盖） |

## 源码修改

无。**本包 0 补丁**（`patches: []`）：上述适配点全部落在配方 cache 变量与 `package_info()` 层，
上游 `CMakeLists.txt` / `src/` / `test/` 一律未改，**未修改任何上游测试用例**。

## 依赖版本

无第三方依赖（`requirements` 为空，`manifest.yaml` 的 `build.dependencies` 为 `[]`）：
上游 relic 自带可移植算术后端，默认 `ARITH=easy` 即自包含；`gmp` / `openssl` 均为可选且本包未启用。
设备侧工具链：clang 15.0.4（hnp）+ CMake 4.1.2 + Conan 2.29.1。

## 验证结果

```bash
# 1) 官方配方验证（内部即干净 conan create）
python3 scripts/ohc-run.py conan-verify relic 0.5.0
#   → G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，Verdict: PASS

# 2) 上游测试：ctest 在配方 build() 内真实执行（TESTS=1）
grep -E "tests passed|Total Test time" archives/r/relic/0.5.0/reports/conan-create.log
#   100% tests passed, 0 tests failed out of 18
#   Total Test time (real) = 159.58 sec
#   （test_bn 159.50s / test_fp 0.30s / …，18 个目标全部 Passed）

# 3) 消费者测试（test_package：安装后编译 + 链接 + 调用 bn_* 公开 API）
grep -E "consumer" archives/r/relic/0.5.0/reports/conan-create.log
#   relic consumer ok: (a + b) - b == a
#   relic consumer ok: (a * a) / a == a
#   relic consumer ok: a * b != 0
#   relic consumer PASSED: 3 assertions

# 4) OPSYS 机制 A/B 对照（同源同参数，仅差一个 -DOPSYS，各约 10s、不编译）
#   A 不注入: -- Configured operating system:   | TIMER:STRING=ANSI | _GNU_SOURCE 覆盖 0/36 flags.make | link.txt 无 -lrt
#   B 注入  : -- Configured operating system: LINUX | TIMER:STRING=HPROC | _GNU_SOURCE 覆盖 36/36 | link.txt 有 -lrt
#   两侧 configure 均退出码 0 —— 这正是该机制「零错误静默退化」的成因
```

## 注意事项

- **CONAN_HOME 与构建路径必须保持纯 ASCII**：设备 `/usr/bin/sed` 是 toybox 实现，对含 UTF-8
  多字节的行做正则匹配会让 configure 的 delimiter 协商失败（同族坑：`could not make ./config.status`）。
- **`conan-verify` / W3 运行期会临时把 `conandata.yml` 的 URL 注入 ghfast 镜像再恢复**：提交前必须
  回读提交态，`git show HEAD:archives/r/relic/0.5.0/conandata.yml | grep -Ec 'ghfast|gh-proxy|file://'`
  必须为 0，并清掉 `conandata.yml.ghfast-bak` 残留文件。
- **`build` 驱动 Step9 的 `conan-init` 会用模板覆盖手写配方**（实测连 `conandata.yml` 的 `filename`
  一起抹掉，直接导致 G2 `BadZipFile`）；恢复手写配方后走 `conan-verify`，不要重跑 `build`。
- 上游 `bench/` 的 16 个基准程序（`BENCH=0`）与 `doc/` 不进包；18 个 ctest 目标即全部测试资产，
  源码树**无** `res` 语料目录、**无** `RUNTEST` 脚本。
---

**编译结束**: 2026-10-15 11:11
**最终状态**: built
