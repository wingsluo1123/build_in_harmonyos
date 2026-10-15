# tzc

Trivial Zephyr Client —— Project Athena Zephyr 通知服务的极简客户端，作为 Emacs
`zephyr-mode` 的子进程运行，通过 stdout 的 s-expression 协议收发 zgram（通知消息）。

## 软件信息

| 字段 | 值 |
|------|-----|
| 名称 | tzc |
| 版本 | 2.6.16.1 |
| 类型 | 命令行工具 (CLI) |
| 许可证 | GPL-2.0-only |
| 上游 | CMU cclub / Darrell Kindred（Debian native 包，2004 年后无新版本） |
| 描述 | Trivial Zephyr Client —— Zephyr 通知服务客户端 |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| zephyr | 3.1.2 | `libzephyr.so.4`，Project Athena Zephyr 通知服务客户端库 |
| e2fsprogs | 1.47.4 | `libcom_err.a`，com_err 错误码表（静态链入） |

## 适配说明

tzc 是 raw Makefile 项目，构建产物为单个可执行文件 `tzc`。

### OHOS 适配要点

1. **编译器切换**：Makefile 内 `CC = gcc` 为 Makefile 赋值，环境变量无法覆盖；
   改用 make **命令行**变量 `make CC=clang`（命令行变量优先级更高）
2. **头文件路径**：通过 `ZEPHYR_INCLUDES` 注入 zephyr 与 e2fsprogs 的 include 路径
3. **库路径**：通过 `ZEPHYR_LIBS` 注入 `-lzephyr -lcom_err` 及两个依赖的 `-L` 路径
4. **无补丁**：`patches: {}`，未修改任何上游源码或构建脚本（R6）

### 构建命令

```bash
make -j1 CC=clang \
  ZEPHYR_LIBS="-lzephyr -lcom_err -L<zephyr>/lib -L<e2fsprogs>/lib" \
  ZEPHYR_INCLUDES="-I<zephyr>/include -I<e2fsprogs>/include"
```

## 验证结果

- conan create: ✅ PASS（`--build=tzc/*` 强制重建）
- conan-verify: ✅ PASS
- W3 本地 CI: ✅ PASS（L0/L1/L2/L4/L5）
- test_package: ✅ PASS（消费者端到端用例 `consumer_test.sh`：A 鸿蒙特有非断言测试 + B 原生真实执行）

## 测试

### 上游测试

tzc 没有自动化测试套件：源码树无 `tests/`/`test/` 目录，Makefile 目标仅
`tzc`/`lread.o`/`tzc.o`/`clean`，`debian/rules` 无测试钩子。

### 适配后测试

test_package 通过 `consumer_test.sh` 执行消费者端到端用例（每步校验退出码）：

**A. 鸿蒙特有非断言测试 —— 原生 ELF 与动态依赖闭包**

1. tzc 为 OHOS aarch64 原生 ELF 可执行文件（`readelf -h`）
2. DT_NEEDED 动态闭包含 `libzephyr.so.4`（`readelf -d`）
3. `com_err` 为已定义符号（非 UND）—— e2fsprogs 静态链入证据（`readelf -sW`）

**B. 端到端消费者用例（原生进程真实执行）**

4. `tzc -o`：加载器完整解析闭包进入 `main()` → 上游真实调用 libzephyr
   `ZInitialize()` → 无 HostManager 时按上游语义输出 elisp 错误并 `EXIT_FAILURE(1)`
5. `tzc --bogus`：真实走上游 getopt/usage 路径，`usage()` 后 `bail(1)`

## 使用方式

```bash
tzc -o          # 仅输出收到的 zgram（不读 stdin）
tzc -e REALM-VISIBLE -l tty  # 指定曝光级别与 zlocation
```

需要 Zephyr HostManager 网络服务方可完成完整业务；通常作为 Emacs `zephyr-mode`
子进程使用。

## PR 信息

- 分支：`feat/tzc-2.6.16.1`
- 状态：built
