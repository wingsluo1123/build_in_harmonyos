# wasi-libc 0.0-git20260129.ec0effd — OpenHarmony PC 适配笔记（路径 C · 高难度挑战）

## 这个包是什么

`wasi-libc` 是面向 WebAssembly/WASI 程序的 libc（POSIX 兼容 C API 的 wasm 实现）。
它**不是**编译给 OHOS 本机用的库：适配产物是一个从源码构建的
`wasm32-wasip1` **sysroot**（`include/` + `lib/wasm32-wasip1/{libc.a,libc.so,crt*.o,libc-printscan-*.a,libwasi-emulated-*.a,…}`），
供下游 wasm 工具链/运行时以 `--sysroot` 方式消费。

上游：<https://github.com/WebAssembly/wasi-libc>，commit `ec0effd`（2026-01-29）。

## 为什么是路径 C（高难度四条件对照）

| 条件 | 判定 | 证据 |
|---|---|---|
| ① 私有系统接口 | 不满足 | 目标是 wasm，不触及宿主内核接口 |
| ② 私有编译工具链 | **硬命中** | 构建必须用带 **WebAssembly 后端**的 C 编译器 + wasm-ld。实测：harmonybrew clang 23.1.1 与 OHOS SDK clang 15.0.4 的 `--print-targets` **均无 wasm**（SDK 版 22 个 target）；官方 wasi-sdk `arm64-linux` 是 **glibc 动态链接**（interp `/lib/ld-linux-aarch64.so.1`），OHOS musl 用户态无法执行。最终自举方案：官方**静态链接** Zig 0.14.0（内嵌 clang+LLVM 19，`zig cc`/`zig wasm-ld`），经 SDK `binary-sign-tool` 自签名后方可在 OHOS 执行 |
| ③ 汇编/闭源二进制/特殊架构 | 部分成立 | 上游含 350+ `.s/.S`（musl 各架构汇编，wasm32 路径不编译；wasm32 专用 `wasi_thread_start.s` 1 个）；产物为 wasm 对象/共享库（`libc.so` 为 wasm 共享库，非 ELF）；setjmp/longjmp 依赖 `__builtin_wasm_throw` + SjLj |
| ④ 全量测试成本极高 | **硬命中** | 上游测试 = **93** 个注册用例（libc-test functional 39 + wasi-libc 自有 54，另含 FS fixture 伪测试），须先编译为 wasm，再在 WASI 运行时执行；OHOS 无 wasmtime（glibc 不可执行）→ 用 Node.js 内建 WASI（preview1）替换 wasmtime 引擎 |

## 构建方案（真机全部实测）

1. 下载静态 Zig 0.14.0（ziglang.org，45MB，真机 ~2.5min）→ `binary-sign-tool`
   自签名 → 得到 wasm-capable `zig cc`（clang 19.1.7）与 `zig wasm-ld`（LLD 19.1.7）。
2. 双面 `clang` 包装器：
   - **编译（-c）→ zig cc**：`--target=wasm32-wasip1` 译为 `-target wasm32-wasi -D__wasip1__`
     （zig 的 target 查询只认 "wasi"，LLVM 19 将其映射为同一 wasip1 triple；补回 `__wasip1__` 宏）；
     剥离 `-resource-dir`；对 `-mllvm -wasm-enable-sjlj` 附加 `-mexception-handling`
     （`__builtin_wasm_throw` 需该 target feature）；**参数边界逐字保留**
     （`-D__wasilibc_printscan_full_support_option="add ... to the link command"`
     这类带空格定义必须保持单 argv 元素）。剪除 zig 自带 wasi/musl 头文件目录
     （zig 注入的 isystem 优先于用户 -isystem，会遮蔽在建 sysroot）。
   - **链接（.o/.a 输入）→ OHOS SDK clang 15 驱动 + `wasm-ld` shim（`zig wasm-ld`，LLD 19）**：
     SDK 的 LLD 15.0.4 缺 `__heap_end`（需 ≥15.0.7，上游 `linker-provided-symbols.txt`
     与 dlmalloc 依赖）；驱动对 `-shared` 按 LLVM 19 语义改走 `-mexec-model=reactor`
     （LLVM 15 默认 command crt 会把静态 dlmalloc 拖进共享库，其 `__heap_end`
     数据引用在共享对象中无法成为 wasm import）。应答 `--print-libgcc-file-name` /
     `-print-resource-dir` 两条 driver 查询（绝对路径对，保证 builtins 拷贝落位）。
3. `cmake -DTARGET_TRIPLE=wasm32-wasip1 -DBUILTINS_LIB=<wasi-sdk-25 官方 wasm32 builtins>
   -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（交叉工具链，编译期探测不链接）；
   `-DFETCHCONTENT_SOURCE_DIR_LIBC-TEST=<预取>` 免配置期克隆；
   `-DENGINE="node;<wasi-run.mjs>"` 用 Node WASI 替换 wasmtime 下载。
4. 构建 `sysroot` 目标 + 全部测试可执行体（91 个 `.wasm`），`ctest` 全量执行。

## 产物（真机实测清单）

`share/wasi-libc/sysroot/`：`include/`（全部公共头）+ `lib/wasm32-wasip1/`：
`crt1.o crt1-command.o crt1-reactor.o libc.a(2.98MB) libc.so(1.42MB)
libc-printscan-long-double.a libc-printscan-no-floating-point.a
libwasi-emulated-{getpid,mman,process-clocks,signal}.{a,so}
lib{crypt,m,ptread,resolv,rt,util,xnet}.a`（空档按上游设计）+ `licenses/`。

## 上游测试结果（真机，Node WASI 引擎）

- ctest 注册 167 项（93 真实用例 + FS setup/cleanup fixtures 等）。
- **152/167 通过（91%）**；15 项失败全部为 **Node-WASI 宿主引擎能力缺口**（非 libc 缺陷），
  逐条证据（errno 取自测试输出）：

| 用例 | 现象 | 引擎缺口 |
|---|---|---|
| opendir / rewinddir / seekdir | `count==2`/`saw_dot` 失败，errno 0 | Node fd_readdir 不合成 `.`/`..`（wasmtime 合成） |
| link / readlink | errno 63 (ENOTSUP) / 42 | Node 未实现 path_link / 符号链接 |
| ioctl | `ioctl(FIONREAD)` errno 63 | Node fd_ioctl 未实现 |
| fcntl / file_nonblocking | `returned_flags==O_WRONLY` 失败 | Node fd_fdstat_get 不回报打开 flags |
| fadvise / fallocate | 期望 0/ENOTSUP 组合 | Node advisory 类 hostcall 行为差异 |
| poll | 返回 -1 | Node poll_oneoff 对普通文件 fd 的限制 |
| utime | `futimens(-1, UTIME_OMIT)` 得 EINVAL（期望 0/EBADF） | Node fd 级 futimens 语义 |
| access / open_relative_path | 期望的失败路径未失败 | Node 权限/flags 判定差异 |

- 非 FS 类全部通过：libc-test functional 39 项中的 37 项（crypt、strtold 等通过）、
  wasi-libc 自有 54 项中的非目录类全部（hello、stdio、字符串、memchr/memcmp 低内存链接
  `--stack-first --initial-memory=327680`、time、clock_nanosleep、getentropy、
  external_env、argv_two_args 等）。

## 消费方式（test_package 实测）

```sh
# 编译（zig cc，wasm 代码生成）+ 链接（SDK clang 驱动 + LLD19 wasm-ld，crt/libc 取自本包 sysroot）
clang-wrapper --target=wasm32-wasip1 --sysroot <pkg>/share/wasi-libc/sysroot test_consumer.c -o consumer.wasm
node wasi-run.mjs --env WASI_CONSUMER_ENV=ohos --dir <tmp>::/ consumer.wasm   # → CONSUMER_PASS
```

消费者覆盖：snprintf/strlen/strstr、malloc+qsort、文件 create/write/read/stat/unlink
（preopen 目录）、time/gmtime_r/strftime、getenv；输出 `CONSUMER_PASS` 且退出码 0。

## 边界与如实申报

- 仅构建 `wasm32-wasip1`（上游默认 triple）。`wasip2/wasip3` 需 `wit-bindgen`/`wasm-tools`/
  `wasm-component-ld`（Rust/glibc 二进制，OHOS 无法执行）重生成绑定，属工具链缺口；
  `-threads` 为上游实验特性，未构建。
- 15 项上游用例受 Node-WASI 引擎缺口影响未通过（见上表，均非 libc 缺陷）；
  曾尝试在 runner 内模拟 wasmtime 的 `.`/`..` readdir 语义（fd_readdir 插接），
  因 Node 原生层绑定 arity 与 preview1 原始签名不一致而放弃，保留诚实分类。
- `check-symbols`（符号清单 diff）为上游可选自检目标，不属测试套件，未纳入门槛。

## CI 侧补充（平台 Worker 网络）

- Worker 网络受限：`ziglang.org` 直连出现 sha256 不匹配（下载被拦/缓存被污染），故 `conandata.yml` 中 zig 首选社区镜像 `pkg.machengine.org/zig/<file>`，`ziglang.org` 作为 fallback；**sha256 固定**保证镜像选择不影响完整性（R39）。
- 源码改用 `github.com/<repo>/archive/<ref>.tar.gz` 单 URL 形式，以便 CI 自动注入 gh-proxy 镜像（URL 列表会关闭该注入）；对应 sha256 已按`archive/` 形式的真实字节重新核验。
- OHOS profile 要求 `settings` 四项齐全：`os, compiler, build_type, arch`（CI L0p 门禁）。
- 宿主工具按 profile 的 `tools.build:compiler_executables` 优先定位链接驱动 clang，并覆盖 harmonybrew `opt`/`Cellar` 与 CI 的 `/data/service/hnp` 布局；`llvm-ar/nm/ranlib` 取该 clang 同目录、`node`（WASI 引擎）多路径发现——避免硬编码 harmonybrew 路径在 CI Worker 上失效。
