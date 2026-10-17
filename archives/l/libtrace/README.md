# libtrace

WAND 网络报文追踪库（LGPL-3.0-or-later）：统一读/写/处理多种抓包格式（ERF、PCAP、PCAP-NG、TSH、DUCK、NDAG），
提供链路/网络/传输层解析、BPF 过滤、并行多线程处理等 API。

- 上游项目：https://github.com/LibtraceTeam/libtrace
- 源码：`https://github.com/LibtraceTeam/libtrace/archive/refs/tags/4.0.34-1.tar.gz`
  （sha256 `b3e73b9ca6757094047295937ab4d834155a0c64674f499132b56e8f81f8fcc9`）
- 版本：`4.0.34`

## OHOS 适配

上游的 GitHub tag 包**不是可直接构建的发行包**：
没有生成好的 `configure`，也没有 `libtrace.h`（它由 `libtrace.h.in` 经 configure 生成）；
而 HarmonyOS 构建宿主只有 `autoconf`/`m4`，**没有 automake / aclocal / libtoolize**，无法 `autoreconf`。

因此配方沿用本仓库 `wandio/4.2.7` 的既有做法，手工复现 configure 的两个产物后直接编译：

1. 生成 `config.h`（libpcap + libwandio 打开，可选后端 DAG/DPDK/pfring/XDP+eBPF/LLVM JIT/wandder/libnuma 全部不定义）；
2. 由 `libtrace.h.in` 生成 `libtrace.h`（占位符含 `@LIBTRACE_MAJOR @` 这种带空格写法，用正则替换）；
3. 用 Conan 配置的 C 编译器编译 `lib/Makefile.am` 中 `libtrace_la_SOURCES` 的基础源文件（45 个），归档为 `libtrace.a`。

补丁 `patches/0001-trace-parallel-pthread-setaffinity-guard.patch`：上游在 `#ifdef __linux__` 里直接调用
`pthread_setaffinity_np()`，而 OHOS 是 musl，**没有这个 glibc 扩展**，会导致链接期未定义符号；
补丁把它改成 feature 宏保护（与同文件里 `HAVE_PTHREAD_SETNAME_NP` 的用法一致），没有该 API 的平台跳过 CPU 绑核。

## 依赖关系

- `libpcap/1.10.6`（必选，读取/注入 pcap 设备与文件）
- `wandio/4.2.7`（必选，上游 4.x 起独立的透明压缩 I/O 库）

## 功能验证

```bash
conan create archives/l/libtrace/4.0.34 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → 消费者用例 12/12：LIBTRACE_CONSUMER_OK
# → 上游用例真跑 37/43：LTEST-SUMMARY total=43 pass=37 compile_fail=0 run_fail=6
```

## 参考

- [上游仓库](https://github.com/LibtraceTeam/libtrace)
- [wandio 依赖](https://github.com/LibtraceTeam/wandio)
