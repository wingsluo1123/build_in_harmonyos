# tzc 2.6.16.1 适配笔记

## 编译环境

- 构建系统: makefile（上游单一 Makefile，raw makefile 项目）
- 编译日期: 2026-10-13
- 编译器: clang 15（OHOS aarch64 profile）
- 目标: HarmonyOS PC / aarch64 / musl
- 状态: built

## 编译步骤

无补丁，全部通过 make 命令行变量覆盖（命令行变量优先级高于 Makefile 内的
`CC = gcc` 赋值）：

```bash
make -j1 CC=clang \
  ZEPHYR_LIBS="-lzephyr -lcom_err -L<zephyr>/lib -L<e2fsprogs>/lib" \
  ZEPHYR_INCLUDES="-I<zephyr>/include -I<e2fsprogs>/include"
```

产物为单个 ELF 可执行文件 `tzc`，装入 `bin/`；man page 与许可证取自上游
`debian/man/tzc.1` 与 `debian/copyright`（Debian native 包布局）。

## 对话记录

### 对话 #1 [2026-10-13]

- 问题: 初次构建时 `libzephyr.so.4`、`zephyr.h`、`com_err.h` 均找不到
- 操作: 确认 OHOS 制品仓中 `zephyr/3.1.2` 提供 libzephyr、`e2fsprogs/1.47.4` 以静态库形式提供 libcom_err；在 build() 中从两个依赖的 cpp_info 取 include/lib 路径注入 `ZEPHYR_INCLUDES` / `ZEPHYR_LIBS`
- 结果: 编译与链接通过，生成 aarch64 ELF

### 对话 #2 [2026-10-13]

- 问题: 早期尝试用环境变量 `CC=clang make` 覆盖编译器无效，Makefile 内 `CC = gcc` 仍生效
- 操作: 改为 make **命令行**变量 `make CC=clang`（命令行变量优先级高于 Makefile 赋值），并删除此前的 Makefile 改写逻辑
- 结果: 工具链切换成功；同时确认 `-Werror=format-security` 在 clang 15 下不报错，**无需**删除该标志，因此**不再需要任何源码/构建脚本补丁**（死补丁一并移除）

### 对话 #3 [2026-10-13]

- 问题: 早期 test_package 只有 `test -x` / `file | grep` / `readelf | grep` 三处断言式检查，且 MANIFEST 声明的命令与实际不符；不满足「至少新增一个鸿蒙特有非断言测试」
- 操作: 重写为 `consumer_test.sh`：A 节鸿蒙特有非断言静态检查（aarch64 原生 ELF、DT_NEEDED 闭包含 libzephyr.so.4、com_err 静态链入证据），B 节原生真实执行（`tzc -o` 触发 libzephyr `ZInitialize()` 走真实业务 API 并优雅 EXIT_FAILURE(1)；`tzc --bogus` 走上游 getopt/usage 路径）
- 结果: `ALL CONSUMER TESTS PASSED`，conan create 全绿

### 对话 #4 [2026-10-13]

- 问题: 上游 Makefile 的 `ZEPHYR_LIBS` 已含 `-lcom_err`，但最终二进制 DT_NEEDED 中**没有** libcom_err
- 操作: 用 `readelf -d` 检查闭包、`readelf -sW` 检查符号绑定
- 结果: 确认 e2fsprogs 在 OHOS 制品仓中以静态库 `libcom_err.a` 发布，`com_err` 符号已静态定义（非 UND）并被链入 tzc；该事实固化为 A3 检查，避免后续误以为链接缺失

### 对话 #5 [2026-10-13]

- 问题: 宿主 python3 用 ctypes dlopen 验证闭包在 CI 上不可靠（HNP python3 受限 linker namespace 会拒绝对缓存路径共享库 dlopen，EACCES）
- 操作: 取消 python dlopen 路线，「闭包真实加载」改由 B 节原生执行承担（加载器必须完整解析整个 DT_NEEDED 闭包才能进入 `main()`；缺库时以 127 退出并输出 shared library 错误，硬失败）
- 结果: 测试结果不随「哪个 python3 运行 conan」而变化，与 xsct 2.3（PR #15143 build #80198）的实证修法一致

## 上游测试清点（R51 三步法）

tzc 为 Debian native 包（上游 CMU cclub），**无上游自动化测试**：

- 源码树（strip 后）文件为 `Makefile` / `tzc.c` / `lread.c` / `lread.h` / `getenv.c` /
  `ZCkAuth.c` / `debian/` / `elisp/`，**无 `tests/` / `test/` 目录，无测试源文件**
- `Makefile` 目标仅 `tzc:` / `lread.o:` / `tzc.o:` / `clean:`，**无 `check` / `test` 目标**
- `debian/rules` 仅 `dh $@`（DH 默认序列），**无测试钩子**；`debian/control` 无
  `Testsuite` 字段

→ `upstream_tests: []`；test_package 不替代上游测试统计。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `zephyr.h` / `com_err.h` 找不到 | 两个头分别来自 zephyr 与 e2fsprogs 包 | 显式声明 `zephyr/3.1.2` + `e2fsprogs/1.47.4`，从 cpp_info 注入 include 路径 |
| 2 | 环境变量 `CC=clang` 不生效 | Makefile 内 `CC = gcc` 覆盖环境变量 | 改用 make 命令行变量 `make CC=clang`（优先级更高），无需补丁 |
| 3 | 最终二进制缺少 libcom_err 依赖 | e2fsprogs 在本仓为静态库发布（`libcom_err.a`） | 无需修复；改为在 A3 中显式验证 `com_err` 符号已静态定义 |
| 4 | conanfile 中读 `compiler_executables` 报错 | OHOS profile 的 `tools.build:compiler_executables` 是 dict 而非单键 | `self.conf.get(..., check_type=dict)` 后 `.get("c")` 取编译器（对照知识库 E392） |
| 5 | 鸿蒙特有测试须为非断言 | 旧 test() 仅 3 处静态字符串断言 | 新增 `consumer_test.sh`：原生真实执行 + 闭包声明校验，全部以退出码判定 |
| 6 | 本地宿主 python dlopen 会假绿/CI 假红 | HNP python3 受限 linker namespace 拒绝 dlopen 缓存路径库 | 移除 python dlopen，闭包真实加载由原生执行强制校验 |

## 源码修改

无 — 纯 make 命令行变量覆盖构建，未修改任何上游源文件或构建脚本。

## 依赖版本

| 依赖 | 版本 | 提供 |
|------|------|------|
| zephyr | 3.1.2 | `libzephyr.so.4`（Project Athena Zephyr 通知服务客户端） |
| e2fsprogs | 1.47.4 | `libcom_err.a`（静态链入，`com_err` 符号） |

两个依赖均已发布至 OHOS 制品仓，`conan download` 可消费（满足 R36 前置）。

## 消费者用例（鸿蒙特有非断言测试）

`test_package/consumer_test.sh`（由 `test_package/conanfile.py` 以 `sh` 调用）：

- **A. 鸿蒙特有非断言测试（静态）**
  - A1 `readelf -h`：tzc 为 ELF / AArch64 原生可执行文件
  - A2 `readelf -d`：DT_NEEDED 闭包含 `libzephyr.so.4`（并打印闭包清单）
  - A3 `readelf -sW`：`com_err` 为**已定义**符号（非 UND）—— e2fsprogs 静态链入证据
- **B. 端到端消费者用例（原生进程真实执行，承担闭包真实加载证明）**
  - B1 `tzc -o`：本机加载器完整解析闭包进入 `main()` → 上游 `say_hi()` 输出
    `; Version 2.6.16` → `setup()` 真实调用 libzephyr `ZInitialize()`/`ZOpenPort()`，
    无 HostManager 时经 com_err 钩子输出 `(tzcspew . error)` 与
    `Hostmanager not responding`，优雅返回 `EXIT_FAILURE(1)`
  - B2 `tzc --bogus`：真实走上游 getopt/usage 路径，`usage: tzc [options]` 后 `bail(1)`
  - 设计约束：不依赖 conan 宿主 python3（HNP python3 受限 namespace 的 dlopen 会被
    EACCES 拒绝，exec 按 DT_NEEDED 加载不受限）

## 验证结果

```bash
# conan create（--build=tzc/* 强制重建）
# recipe: tzc/2.6.16.1@ohpcd/stable
# binary: 已创建并执行 test_package
# result: PASS
# test_package: consumer_test.sh -> ALL CONSUMER TESTS PASSED

# W3 本地 CI
# L0: PASS  L1: PASS  L2: PASS  L4: PASS  L5: PASS
```

## 注意事项

- tzc 运行时需要 Zephyr HostManager 网络服务才能完成完整业务（订阅、收 zgram）；
  无头/无服务环境下消费者用例改以「闭包真实加载 + 原生执行到 Zephyr 运行时路径」验证
- 运行期 `libzephyr.so.4` 经 Conan 运行时环境（VirtualRunEnv 的 `LD_LIBRARY_PATH`）
  解析；直接裸跑需自行设置 `LD_LIBRARY_PATH`
- tzc 与 Emacs zephyr-mode 通过 stdout 的 s-expression 协议通信（`(tzcspew . …)`）
---

**编译结束**: 2026-10-13 15:25
**最终状态**: built
