# tracexec — OpenHarmony 编译档案

## 软件简介

tracexec 是一个用于追踪 `execve{,at}` 与 pre-exec 行为的命令行工具
（"程序执行时到底跑了什么、怎么跑的"），同时可作为调试器启动器。
纯 Rust 实现（Cargo 工作区，2024 edition），核心是 ptrace 后端
（libseccomp 优化）与实验性 eBPF 后端。

- 上游：<https://github.com/kxxt/tracexec>
- 许可证：GPL-2.0-or-later
- 语言：Rust（Cargo）

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.17.0 | ✅ built | 上游 v0.17.0；`--no-default-features` 构建（eBPF 后端关闭，鸿蒙内核无 BPF syscall）；ptrace 后端经 `libseccomp/2.6.1` 链接 libseccomp |

## 适配要点（OHOS aarch64）

1. **Rust 工具链**：以 `tool_requires("rust-toolchain/1.97.1")` 引入（竞赛 CI 无
   系统 Rust）；官方 dist 二进制未签名，OHOS 拒绝 execve（EACCES），配方将
   `cargo`/`rustc` + `librustc_driver-*.so` 复制后用 `binary-sign-tool -selfSign 1`
   自签名，其余只读负载软链（保持 rustc sysroot 推导，无需显式 `--sysroot`）。
2. **eBPF 后端关闭**：鸿蒙内核无 BPF syscall（`bpf()` 不可用），eBPF 后端运行期
   无法工作；上游 CI 本就包含 `no-default-features`（eBPF 关闭）变体。构建命令
   为 `cargo build --release --locked --target aarch64-unknown-linux-ohos
   --no-default-features --bin tracexec`。
3. **libseccomp**：ptrace 后端的 `libseccomp-sys` 链接 `-lseccomp`，消费制品仓
   共享包 `libseccomp/2.6.1`（`LIBSECCOMP_LIB_PATH`/`LIBSECCOMP_LINK_TYPE=dylib`，
   运行时 `libseccomp.so.2` 经 Conan 运行环境解析）。
4. **链接器覆盖**：上游 `.cargo/config.toml` 把全部 aarch64 目标的 linker 固定为
   `aarch64-linux-gnu-gcc`（OHOS 不存在）；配方以 `cargo --config
   target.aarch64-unknown-linux-ohos.linker=<OHOS clang>` 覆盖。
5. **cargo 运行库**：cargo 动态链接 libssl/libcrypto/libz（OHOS loader 忽略
   DT_RUNPATH），取自 Harmonybrew OHOS bottle 注入 `LD_LIBRARY_PATH`；
   crates 走 rsproxy.cn 镜像 + CA bundle 注入。

## 已知限制（如实声明）

- **ptrace 内核策略**：OHOS 对无特权进程拒绝 ptrace（实测 `PTRACE_TRACEME`
  返回 EPERM），因此 tracexec 的追踪功能在无特权环境下无法实际运行
  （`tracexec log/tui/collect -- cmd` 会干净地报权限错误）；`--version` /
  `--help` / `generate-completions` 等 CLI 功能正常。同设备先例：ceccomp 的
  probe/trace/seize 动态测试同样因 ptrace 策略失败（如实记录）。
- **eBPF 模式**：不可用（内核无 BPF syscall，上游构建即关闭）。
- 详见 `0.17.0/notes.md` 与 `0.17.0/reports/test-report.md`。

## 验证

- 上游测试：cargo 工作区逐包执行（release profile），实测统计见
  `0.17.0/reports/test-report.md`（平台策略导致的失败/跳过逐项列明）。
- 消费者测试：`test_package/`（4 项鸿蒙特有 + 6 项消费者断言）。
