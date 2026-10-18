# DRAFT: OHOS 默认 emulated TLS 破坏 version script 的 TLS 符号导出

- **状态**：草稿（随 SPDK 25.05 适配 PR 一起提交）
- **来源事件**：spdk 25.05（捆绑 `spdk/dpdk@cf36799` = DPDK 25.03.0）在 OHOS
  aarch64 上链接共享库失败（2026-10-15）
- **分类**：libc / portability / linking / build-system
- **严重度**：3（blocking）

## 现象

用 OHOS clang 构建 DPDK 25.03.0 时，`librte_eal.so` 已成功产出，但所有依赖它的
共享库（`librte_ring.so`、`librte_timer.so`、`librte_dmadev.so`、`librte_acl.so`、
`librte_stack.so`、`drivers/librte_bus_pci.so`、`drivers/librte_bus_vdev.so` …）
在链接阶段失败：

```
ld.lld: error: undefined symbol: __emutls_v.per_lcore__rte_errno
>>> referenced by eal_common_errno.c
>>>               librte_eal.a.p/eal_common_eal_common_errno.c.o:(rte_errno_get)
ld.lld: error: undefined symbol: __emutls_v.per_lcore__lcore_id
ld.lld: error: undefined symbol: __emutls_v.per_lcore_trace_mem
ld.lld: error: undefined symbol: __emutls_v.per_lcore_trace_point_sz
ld.lld: error: undefined symbol: __emutls_v.per_lcore__thread_id
...
```

`--no-undefined` 下这些库要求所有符号可解析，于是整条 DPDK 共享库链断裂。

## 根因

OHOS 的 clang（harmonybrew clang 23.1.1，target `aarch64-unknown-linux-ohos`）**默认
启用 emulated TLS**（等价 `-femulated-tls`）。同一段代码：

```c
__thread int x;
int getx(void){ return x; }
```

两种模型产出的符号完全不同：

```
# 默认（emulated TLS）
$ clang -c -fPIC tls.c -o tls.o
$ llvm-readelf -s tls.o | grep -E 'x$|emutls'
     6: ... OBJECT  GLOBAL DEFAULT  4 __emutls_v.x
     7: ... NOTYPE  GLOBAL UND    __emutls_get_address

# 关闭后（原生 TLS）
$ clang -c -fPIC -fno-emulated-tls tls.c -o tls2.o
$ llvm-readelf -s tls2.o | grep -E 'x$|emutls'
     6: ... TLS     GLOBAL DEFAULT  4 x
```

emulated TLS 下，变量 `x` 变成一个 32 字节控制块 `__emutls_v.x`（定义在声明该变量的
翻译单元里），取值经运行时函数 `__emutls_get_address` 间接完成。

对**单个可执行文件**这没有问题。问题在**共享库 + ELF version script** 的组合：

1. DPDK 每个库都带 `version.map`，由 `--version-script` 控制导出符号。脚本里写的是
   业务符号（`rte_*`、`per_lcore__*` 等），**不会**列出 `__emutls_v.*` 这类编译器
   内部符号。
2. 于是定义 `RTE_DEFINE_PER_LCORE(int, _rte_errno)` 的 `librte_eal.so`，在版本脚本
   过滤下**不导出** `__emutls_v.per_lcore__rte_errno`（`local: *` 把它隐藏了）。
3. 其它 `.so` 引用该控制块时即 `undefined symbol`。

根本矛盾是：**编译器的默认 TLS 模型（emulated）与 ELF 符号版本脚本“TLS 即符号本身”的
假设不一致**。glibc/gcc 平台默认原生 TLS，所以上游从来没有暴露这个问题。

## 与既有知识条目的边界

- **E026**（`TLS, __thread, _Thread_local, thread_local, tls_model, glibc extension,
  musl, pthread`）描述的是“编译期不支持 TLS / musl 不支持 `__attribute__((tls_model))`”，
  error_signature 为 `thread-local storage not supported | tls_model.*unsupported`。
  **本坑不同**：OHOS 运行期**支持**原生 TLS，编译期也从不报错；问题纯粹是默认选了
  emulated TLS，导致控制块符号与版本脚本的导出集合冲突，签名是链接期
  `undefined symbol: __emutls_v.*`。
- 与 E531（qsort_r）等无关。
- kb 查重：`emutls` / `emulated-tls` / `__emutls_v` 均为 **0 命中**（0 正式条目、0 草稿）。

## 处方

**首选：`-fno-emulated-tls`（改用原生 TLS）**

```sh
# 普通 C/C++ 工程
CFLAGS="$CFLAGS -fno-emulated-tls" CXXFLAGS="$CXXFLAGS -fno-emulated-tls" ...

# meson 交叉构建（DPDK 场景）
meson setup build --cross-file cross.txt \
  -Dc_args=-fno-emulated-tls -Dcpp_args=-fno-emulated-tls ...

# Conan 配方：随包传播，避免消费者混用两种模型
self.cpp_info.cflags = ["-fno-emulated-tls"]
```

OHOS 运行时（bionic/musl 系）支持原生 TLS；实测跨 `.so` 读写线程局部变量正常
（`libtls.so` 里 `__thread int x`，主程序 `-fno-emulated-tls` 链接后读写正确）。

**次选：把内部符号加入导出白名单**（不推荐，仅当必须保留 emulated TLS）

```
# version.map
{ global: rte_*; __emutls_v.*; __emutls_get_address; local: *; };
```

缺点：符号随变量膨胀、可读性差，且必须保证 `__emutls_get_address` 在运行时可解析。

## 复现与验证

```sh
SDK=$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin
printf '__thread int x;\nint getx(void){return x;}\n' > t.c
$SDK/clang -c -fPIC t.c -o t.o          # 看 __emutls_v.x
$SDK/llvm-readelf -s t.o | grep -E 'x$|emutls'
$SDK/clang -c -fPIC -fno-emulated-tls t.c -o t2.o   # 看原生 TLS x
$SDK/llvm-readelf -s t2.o | grep -E 'x$|emutls'
```

端到端：DPDK 25.03.0 在加 `-fno-emulated-tls` 前所有依赖 EAL 的 `.so` 链接失败；
加入后 DPDK（含 `bus/pci`、`bus/vdev`、`mempool/ring`）与上层 SPDK 25.05 均
`conan create` **RC=0**。

## 适用范围（复用性）

- 任何在 OHOS clang 上、用 `__thread`/`_Thread_local`/`RTE_DEFINE_PER_LCORE` 并
  通过 version script / 可见性控制导出、又被其它共享库引用的 C/C++ 项目。
- 典型嫌疑：DPDK 及所有内嵌 DPDK 的项目（SPDK、VPP、FD.io、Open vSwitch 等）、
  自研 per-thread 缓存且对 `.so` 做符号版本控制的库。
- 纯静态库/单可执行文件不受影响（无跨 `.so` 的控制块解析问题）。
