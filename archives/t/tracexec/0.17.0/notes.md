# tracexec 0.17.0 — 适配笔记（HarmonyOS PC / aarch64）

## 1. 软件与源码

| 项 | 值 |
|----|----|
| 名称 | tracexec（execve{,at} 与 pre-exec 行为追踪器、调试器启动器） |
| 版本 | 0.17.0（GitHub tag `v0.17.0` = commit `ecbda651a4006789debf565376cd6f37241dec3e`，2026-03-08） |
| 上游 | <https://github.com/kxxt/tracexec> |
| 语言 | 纯 Rust（Cargo 工作区，edition 2024，rust-version 1.88）/ Cargo |
| 许可证 | GPL-2.0-or-later |
| 源码包 | `https://github.com/kxxt/tracexec/archive/refs/tags/v0.17.0.tar.gz` |
| sha256 | `c3481cf1f23ad9fa33247c5294ab204fa5a5b9a39e1ca9b24ffa631211a55c75` |
| 产物 | `bin/tracexec`（可执行；`commands.json` 在软件级目录，R38） |

## 2. 依赖检查（W0）

`Cargo.toml`/`Cargo.lock` 依赖全为 crates.io crate（经 rsproxy.cn 镜像拉取），
C/C++ 目标依赖仅有 libseccomp（ptrace 后端 `libseccomp-sys` → `-lseccomp`），
eBPF 后端（libbpf）因平台无 BPF syscall 不参与构建（见 §5.2）。conan 层面消费：

| 依赖 | 角色 | W0 验证 |
|------|------|---------|
| `rust-toolchain/1.97.1` | 构建工具链（`tool_requires`） | `conan download rust-toolchain/1.97.1 -r=ohpcd` EXIT=0（armv8 OHOS 二进制） |
| `libseccomp/2.6.1` | ptrace 后端共享库（`requires`） | `conan download libseccomp/2.6.1 -r=ohpcd` EXIT=0（armv8 OHOS 共享二进制，含 seccomp.h + libseccomp.so/.so.2） |

## 3. 语言预检（R47）

```
$ python3 scripts/ohc-run.py lang-preflight tracexec 0.17.0 --src <src> --lang rust
✅ 语言匹配: task=rust, detected=rust
  build_system=cargo, manifest="Cargo.toml name = \"tracexec\"",
  source_stats=源文件 93 个（rust:92, bash:2, c:1），主体占比 99%
```

> 平台任务元数据 `lang` 字段为 `cpp`（该批多个纯 Rust 任务同款元数据，如
> zizmor/weggli/rhai/rudof 等均以 Rust 适配合入）；按实测源码与既有先例以
> **rust** 执行语言预检与适配。

## 4. 构建方式

```bash
cargo build --release --locked --target aarch64-unknown-linux-ohos \
    --no-default-features --bin tracexec
```

关键构建环境（配方 `build()` 内自足定义，R33）：

| 变量 | 值/来源 | 原因 |
|------|---------|------|
| 工具链 | `rust-toolchain/1.97.1` 包内 cargo/rustc 复制到 build 目录 + OHOS 自签名 | 官方 dist 二进制无 code signature，OHOS 拒绝 execve（EACCES） |
| `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER` + `--config target.aarch64…linker=` | OHOS SDK `aarch64-unknown-linux-ohos-clang` | 上游 `.cargo/config.toml` 把 aarch64 目标 linker 固定为 `aarch64-linux-gnu-gcc`（OHOS 不存在） |
| `LD_LIBRARY_PATH` | 工具链 lib + openssl bottle lib + libseccomp lib + SDK llvm/lib | cargo 动态链接 libssl/libcrypto；测试二进制链接 libseccomp |
| `LIBSECCOMP_LIB_PATH`/`LIBSECCOMP_LINK_TYPE=dylib` | `libseccomp/2.6.1` 包 lib 目录 | `libseccomp-sys` build.rs 契约（无 pkg-config） |
| `CARGO_HOME` | build 目录私有 + `config.toml` 指向 rsproxy.cn 稀疏镜像 + CA | 设备无 crates.io CA 链；镜像有 CA bundle |
| `TMPDIR` | build 目录私有 tmp | OHOS `/tmp` 只读（E002） |
| `CARGO_BUILD_JOBS=2` | 共享设备礼让 | 多人共用一台机器 |

## 5. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 嵌套源码检测把源码错误提升为 `demonstration/gdb-launcher`（仅 6 个文件） | F068 `_BUILD_MARKERS` 仅含 configure/CMakeLists/Makefile/meson.build，**不含 Cargo.toml**；tracexec 根目录无这些标记，递归找到演示子目录的 Makefile 并"提升" | 手工重建 `.orig`（tar 正确解包 + `.tarball-sha256`）与 `.work`，并用 `ohc.edit_tracker.snapshot` 重建基线指纹（465 文件）；工具缺陷已记入 SKILL 反馈 |
| 2 | `cargo --version` 报 `Error loading shared library libssl.so` | rust-lang 官方 dist cargo 动态链接 libssl/libcrypto/libz；OHOS 系统 OpenSSL 3.0 缺 `SSL_get0_group_name` 等 cargo 1.97 需要的符号 | 使用 Harmonybrew OHOS bottle `openssl@3-3.6.5`（构建期专用，sha256 实测锁定）；`libz.so` 由 musl 默认路径 `/usr/lib/libz.so.1` 解析，无需额外 bottle |
| 3 | 旧配方中的 bottle URL 全部 404 | harmonybrew CDN bottle 被轮换（`openssl@3-3.6.4_1`/`3.6.4`/`3.6.3`、`zlib-ng-compat-2.3.3_2/_1` 实测 404；`brew fetch` 自身也 404） | 用 `brew fetch openssl@3` 探测当前版本（3.6.5）并实测下载 + sha256；配方仅锁定这一个 bottle（`cargo_runtime`） |
| 4 | `rustc` 复制签名后编译报错风险（E0463 can't find crate for std） | 搬迁 rustc 会破坏其 sysroot 推导（DRAFT-13336） | 仅复制需要 exec 的 `cargo`/`rustc`/`librustc_driver-*.so` 并签名，其余只读负载**软链**到签名目录（`<bin>/../lib/rustlib` 存在），sysroot 推导保持正确，无需显式 `--sysroot` |
| 5 | eBPF 后端在 OHOS 不可用 | 鸿蒙内核无 BPF syscall（`archives/l/libbpf` README + 实测）；ebpf 模式还需 root | 以 `--no-default-features` 构建（上游 CI 本就包含该变体）；`--help` 不再出现 `ebpf` 子命令 |
| 6 | tracexec 追踪功能在设备上不可用 | OHOS 对非特权进程整体禁用 ptrace：`PTRACE_TRACEME/ATTACH/SEIZE` 与 `process_vm_readv` 全部 EPERM（errno=13），`PR_SET_PTRACER` EINVAL，`CapEff` 无 CAP_SYS_PTRACE（与 DRAFT-10103/reptyr 同款实测） | 如实申报平台边界：能力探针证据 + 上游测试逐项登记；消费者测试覆盖 CLI 可用行为面（version/help/completions/错误处理/EPERM 干净报错） |
| 7 | 编译错误 `E0432: unresolved imports nix::libc::PTRACE_GET_SYSCALL_INFO / ptrace_syscall_info`（guards.rs） | libc 的 `PTRACE_GET_SYSCALL_INFO` 请求常量与 `ptrace_syscall_info` 结构仅定义在 `linux/gnu` 模块；OHOS（musl 系 target_env）没有 | 补丁 0001：`#[cfg(target_env = "ohos")]` 局部 shim（内核 uapi `linux/ptrace.h` 布局，架构无关；请求常量取 `c_int` 以匹配 musl 系 `ptrace()` 签名），其余目标保持原始 libc import 不变 |
| 8 | 编译错误 `E0277: *mut c_void: Send/Sync`（tracer.rs 线程 tid 通道与 `RunningTracer`、main.rs 的 tokio::spawn） | OHOS `libc::pthread_t = *mut c_void`（musl 定义），既非 Send 亦非 Sync：`SyncSender<pthread_t>` 无法移入 `spawn_blocking`，`?` 亦无法转换 `SendError`，`RunningTracer` 也因此非 Send | 补丁 0002：通道与 `RunningTracer.tid` 改存 `usize`，`pthread_kill` 调用处 cast 回 `pthread_t`（全平台等价） |
| 9 | conan-verify 的 E017 镜像注入（ghfast.top）超时导致 source() 下载失败（github.com 直连同样超时） | 设备到国际网络瞬断；工具注入后无回退 | 用 conan 源缓存（`core.sources:download_cache`，按 sha256 键）预置 tarball（本地验证环境措施，不入仓）；CI 侧走平台自身的镜像 fallback/预下载缓存 |
| 10 | 上游测试 9 项平台边界失败/不适用 | ptrace 全禁（4 项 tracer E2E + smoke）；OHOS seccomp 施行/errno 差异（seccomp_filter_loads）；HMDFS 忽略 chmod（test_read_interpreter_inaccessible，E046）；`/proc/stat` `btime 0`（2 项 boot-time 断言） | 逐项登记为 `--skip` 平台过滤（技术原因+实测证据，见 reports/test-report.md）；其余 164 项真实运行且通过 |
| 11 | 所有子命令启动即失败：`Failed to parse kernel major ver!`（含 `generate-completions`） | OHOS `uname -r` 返回 `HongMeng Kernel 1.12.0`，不以 Linux 式版本号开头，`is_current_kernel_ge` 解析失败并经 `?` 在命令分发前中止 | 补丁 0003：解析失败按"不等于 >= min_support"处理（走上游既有的旧内核告警路径），非追踪命令（generate-completions）恢复可用；追踪命令继续走到平台边界并用告警如实提示内核不受支持 |
| 12 | 本地 CI 门禁（build_and_test.sh）预下载改写后 cargo 运行库文件找不到：`FileNotFoundError: predl_cache/fd78302f_openssl@3-3.6.5...tar.gz` | CI 预下载枚举 conandata 全部 URL 并以"保留百分号编码"的文件名缓存（`...openssl%403-...`），随后把 URL 改写为 `file://`；conan 的 file:// 处理会解码 `%40`→`@`，与缓存文件名不一致 | 将 bottle URL+sha256 从 conandata 移到配方常量 `CARGO_RUNTIME_BOTTLES`（rumdl 同款，绕开该重写）；同时移除 build() 中重复的 `apply_conandata_patches`（source() 已应用） |
| 13 | 平台 CI `conan-build-test` 失败：编译期 `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`（build script 链接阶段） | CI Worker 共享且高负载，cargo 并行编译 + clang 链接子进程把进程/内存配额打满（Rust 全量构建链接密度高） | 配方增强：`cargo build`/逐包 `cargo test` 失败且输出命中资源耗尽特征（`Resource temporarily unavailable`/`posix_spawn failed` 等）时，自动以 `CARGO_BUILD_JOBS=1` **串行重试一次**（cargo 增量续跑，代价小）；重试仍败才报错 |
| 14 | 平台 CI `conan-build-test` 失败：test_package A6 在 Worker 挂起（`timed out after 60s/30s (hang); partial=''`——无输出、无退出；本机快速干净报错） | Worker（CI-033/009/003 多次复现）上 `log` 默认 `foreground=true` 的终端前台语义与 Worker 内核对追踪入口（默认 `--seccomp-bpf auto` 会在 tracee 内装载 seccomp 过滤）的处理共同导致探测不返回；上游测试夹具即用 `foreground=false` | A6 改**非交互分级探测**：`--no-foreground` + stdin=/dev/null + 独立会话；① `--seccomp-bpf off` ② 再退 `--polling-interval 1000`；每级 30s 硬超时 + 超时杀进程组并回显部分输出；两级均超时才按平台边界 **skip**（harness 强制有界，留证）；成功追踪/干净报错/崩溃/panic 的判定语义不变 |

## 6. 源码修改

共 3 个补丁，均为 OHOS 工具链（libc musl 系定义）/内核字符串差异的便携性修复，不改 tracexec 业务逻辑，
不含 `__OHOS__` 宏注入（用 `cfg(target_env = "ohos")` 的实质分支或等价的语义保持改动）：

| 补丁 | 修改 | 说明 |
|------|------|------|
| `0001-...guards.rs.patch` | +72/-7 | libc 的 `PTRACE_GET_SYSCALL_INFO`/`ptrace_syscall_info` 仅 linux/gnu 模块提供；加 `cfg(target_env="ohos")` 局部 shim（uapi 精确布局），其余目标原样 |
| `0002-...tracer.rs.patch` | +6/-4 | OHOS `pthread_t = *mut c_void` 非 Send/Sync；tid 通道与 `RunningTracer.tid` 改存 `usize`（pthread_kill 处 cast 回），全平台等价 |
| `0003-src-main.rs.patch` | +8/-1 | OHOS uname 版本串无法解析时按"不满足最低内核"处理（警告路径）而非中止，恢复非追踪子命令可用 |

此外的适配均在构建环境/配方层完成（工具链复制签名、linker 覆盖、eBPF 关闭走官方 feature 开关）。

## 7. 依赖版本

| 依赖 | 版本 | 备注 |
|------|------|------|
| rust-toolchain | 1.97.1 | tool_requires（仓内基础设施包，Route B 前置） |
| libseccomp | 2.6.1 | requires（ptrace 后端；共享链接，运行期经 Conan runenv 解析） |
| openssl（构建期 cargo 运行库） | 3.6.5 | Harmonybrew OHOS bottle，仅构建期，不入包 |

## 8. 验证结果

```bash
# conan create（G2，干净源码，OHOS aarch64 profile）
conan create archives/t/tracexec/0.17.0 \
    -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device   # 详见 reports/test-report.md

# 消费者测试（test_package）
PACKAGE_FOLDER=<pkg> python3 test_tracexec.py

# 平台能力探针（如实证据；探针原始输出为设备本地实测、不随 PR 提交，
# 关键 EPERM 矩阵已内联于 reports/test-report.md §1.3）
./ptrace_matrix
```

- 上游测试：实测运行 164 / 通过 164（100%），平台边界过滤 9 项（逐项原因见
  `reports/test-report.md`：ptrace 策略 5、seccomp 施行差异 1、HMDFS chmod 1、
  /proc/stat btime=0 2）
- 消费者测试：10 项断言（4 项鸿蒙特有 + 6 项消费者）→ `reports/test-report.md`

## 9. 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` / `conandata.yml` | Conan 配方（构建期环境自足） |
| `test_package/` | 消费者测试（真实运行 tracexec CLI + 鸿蒙特有断言） |
| `../../commands.json` | CLI 工具声明（R38，软件级） |
| `reports/test-report.md` | 测试统计与平台边界登记 |
| `reports/audit-result.json` | W4 独立审计结论 |

## 10. 注意事项（已知限制，如实声明）

1. **ptrace 平台边界**：OHOS 非特权进程 ptrace 全禁（EPERM 实测矩阵见报告）。
   `tracexec log/tui/collect -- cmd` 在该环境会干净报权限错误；这是平台安全策略，
   用户态无法绕过。有权限环境（root/系统域）下后端逻辑不受本适配影响。
2. **eBPF 后端关闭**：内核无 BPF syscall，上游 `ebpf` 子命令与特性不构建。
3. 追踪相关的上游测试在设备上按平台边界登记（不桩化、不弱化断言；R34/R51）。

**编译结束**: 2026-10-12（详见 reports/test-report.md）
