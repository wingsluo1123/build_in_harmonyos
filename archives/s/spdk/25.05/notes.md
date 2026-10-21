# SPDK 25.05 — OHOS 适配笔记

## 结论

- 配方：`archives/s/spdk/25.05/`，`package_type=library`（静态，`shared=False`）。
- 上游：`v25.05`（`VERSION 25.05.0`），捆绑 DPDK fork `spdk/dpdk@cf36799`（25.03.0）。
- 依赖：`libuuid/2.42.2`、`openssl/3.5.6.1`、`libaio/0.3.112.1`（均在 ohpcd 制品仓，
  有 OHOS 二进制）；构建期 `tool_requires pyelftools/0.33`（DPDK pmdinfogen），
  测试期 `test_requires cunit/2.1-3`。
- 构建：SPDK `./configure` + `make`；DPDK meson/ninja 交叉构建。clang 15 / OHOS 6.0
  aarch64，主机三元组 `aarch64-unknown-linux-ohos`。
- 产物：`include/spdk/**`（96 头）+ 捆绑 DPDK 头；`lib/libspdk_*.a`（67，排除两项测试支持库）+
  `lib/librte_*.a`（60）。
- 真机 `conan create` **RC=0**：消费者测试 6/6。
- **运行边界（如实申报）**：DPDK EAL 需要 hugepage/vfio/uio/`/sys` 等 OHOS 不提供的
  私有内核接口，SPDK 数据面无法在 OHOS 上实跑。默认对外暴露的链接集是 CPU-only、
  不依赖 EAL 运行时的 `spdk_util`/`spdk_log`/`spdk_json`；其余库照常编译打包。

## 关键适配点（按踩坑顺序）

1. **捆绑 DPDK 且必须交叉构建**。SPDK 没有非 DPDK 的 `env` 实现，`configure` 默认
   要求 `spdk/dpdk` 子模块；而子模块不在 tarball 里。配方 `source()` 单独下载 pinned
   commit 的 DPDK，配方内先构建出前缀，再用 `--with-dpdk=<prefix>` 交给 SPDK。

2. **DPDK 交叉文件**。meson 交叉构建时 `cpu_instruction_set = host_machine.cpu()`，若
   `cpu='aarch64'` 会套 `-march=aarch64` 失败。官方 aarch64 交叉文件用
   `cpu='armv8-a'` + `[properties] platform='generic'`；aarch64 的 `platform` 取自
   交叉文件属性（不是 `-Dplatform`）。`numa=false` 关闭 libnuma 探测。

3. **emulated TLS（最关键、最隐蔽）**。OHOS clang 默认 `-femulated-tls`：`__thread`
   变量编译成 `__emutls_v.<name>` + `__emutls_get_address`。DPDK 的每核变量
   （`per_lcore__rte_errno` 等）由 `version.map` 控制导出，脚本里没有 emutls 控制符号
   → 链接 `librte_ring.so` 等报
   `ld.lld: error: undefined symbol: __emutls_v.per_lcore__rte_errno`。DPDK 与 SPDK
   统一加 `-fno-emulated-tls`（原生 TLS）后全部通过；实测 OHOS 原生 TLS 的跨 `.so`
   线程局部变量读写正常。

4. **`sockaddr_storage` 重定义（KB E091/E119）**。OHOS `<linux/socket.h>` 与
   `<sys/socket.h>` 都定义 `struct sockaddr_storage`。DPDK `eal_dev.c`（netlink）、
   `vhost.h`（linux/if.h）、SPDK `env_dpdk/pci_event.c`（netlink）受影响，按 E091
   处方作局部 UAPI 类型重命名，包含头文件后 `#undef`，不引入平台条件宏。

5. **bionic libc 缺口**：
   - 无 `pthread_cancel`（E085/E127）：DPDK `eal_common_proc.c` 的 mp 线程清理、
     `eventdev/rte_event_eth_rx_adapter.c` 的中断线程改用协作退出：
     mp 线程以 100 ms `poll` + 非阻塞 `recvmsg` 检查原子 fd 停止状态；中断线程以
     原子停止标志和 100 ms `rte_epoll_wait` 退出。两处都保留 `join`，结束后才关闭
     socket 或释放 ring/event 缓冲；join 失败时保留线程仍可能访问的资源。
   - 无 `pthread_setaffinity_np`/`pthread_getaffinity_np`：DPDK `rte_thread.c`、
     `telemetry.c` 通过 Meson 探测 libc 能力。支持 pthread affinity 时保留
     原调用；否则使用已探测的 `pthread_gettid_np` + `sched_*affinity`，不支持时
     返回 `ENOTSUP`（telemetry 的绑定为可选），不把 bionic 扩展强加给 glibc。
   - 无 glibc `program_invocation_short_name`：`eal.c` 改用 `argv[0]` 的 basename。

6. **ISA-L**。`configure` 在 aarch64 上默认启用 ISA-L 并要求 `isa-l/autogen.sh`；ISA-L
   的汇编要求 GNU `as` ≥ 2.24，OHOS 无此汇编器。补丁把启用条件收紧为
   `sysname == "Linux"`，非 Linux（OHOS）直接关闭 ISA-L 及压缩/加密软件后端。

7. **杂项**：SPDK `bdev_aio` 的 `FALLOC_FL_ZERO_RANGE` 在 OHOS `<fcntl.h>` 不可见 →
   `#include <linux/falloc.h>`；DPDK `pmdinfogen` 需要 PATH 上的 `ar` → 构建时
   提供 `ar → llvm-ar` shim；HMDFS 不支持 make jobserver 的 FIFO → 
   `make --jobserver-style=pipe`。

## 测试与计数

配方使用 `test_requires cunit/2.1-3`、`--enable-unit-tests`，正常构建上游单测。
`run_unit_tests.py` 按顺序运行全部已构建的 CUnit 程序，为每个程序保存原始日志，
从 CUnit Run Summary 读取 total/ran/passed/failed/inactive；失败、超时或缺少汇总都会使构建失败。
运行结果随包保存为 `res/summary.json`，消费者读取该结果，避免硬编码“通过”。
测试支持库 `libspdk_ut.a`、`libspdk_ut_mock.a` 不安装，CUnit 不成为消费者运行依赖。

- 上游源码有 **122 个测试程序目标**，不是 122 个内部用例。
- **1376 处 CU_ADD_TEST + 8 处 CU_add_test = 1384 个注册位置**。
  Blob 等测试在多个配置下重复注册，注册位置数不等于运行时用例数。
- 相同功能配置下，未加 DIX 功能守卫的基线是 **1636 个注册用例**；
  独立 `accel_ut --list` 对照为 25 → 24，唯一差异是 `test_sequence_dix`。
- 当前配置 **103 个程序、1635/1635 用例通过，0 失败、0 inactive**。
  相对基线是 **1635/1636（99.94%）**，1 个 DIX 加密序列用例因 ISA-L crypto
  关闭而未注册；不把该用例记作通过。独立 DIX 生成/校验序列仍运行。
- 另有 **19 个可选模块测试程序、144 个源码注册位置**未构建：RDMA、FC、vhost、
  io_uring、idxd、压缩/加密设备、CUSE、vfio-user 等模块在配方中关闭。
  清单由 runner 自动写入 `unbuilt_programs`；不声称覆盖所有可选后端。
- 消费者是 **1 个程序、6 项检查**：CRC-32C/CRC-32(IEEE) 标准向量
  `123456789`、两项增量一致性，以及 Base64 编解码往返；不混入上游统计。

## 本轮测试修复

1. `0004`：为上游 `lib/ut_mock` 增加两个 robust mutex 调用的测试模拟，
   与已有 mutex 初始化模拟共同隔离 OS 依赖；仅测试 SPDK 逻辑，不证明鸿蒙支持
   robust/process-shared mutex。安装库不含这两个模拟，测试断言不变。
2. `0005`：file 和 NVMf reservation 测试的临时文件改为相对路径；runner 为每个
   程序建立独立可写目录。原始 file 测试因 `/tmp` 不可写真实失败 0/2，修复后 2/2。
3. `0006`：DIX 加密序列与现有 crypto 序列使用相同的 `SPDK_CONFIG_ISAL_CRYPTO`
   功能条件；原测试在后端关闭时创建 AES-XTS key 返回 ENOTSUP，fatal assertion 后
   清理等待无法结束。明确排除该 1 项，未修改预期值或断言。
4. `0007`：生产 `nvme_tcp.h` 的两个 HKDF 空盐参数由 NULL,0 改为非空指针,0，
   保持空盐语义，解决 OpenSSL 3.5.6 参数拒绝问题。上游 PSK 已知结果断言不变。
   参考：[OpenSSL #31067](https://github.com/openssl/openssl/issues/31067)。
5. `0008`：认证 Failure1 的生产实现延迟 100ms 断连，原测试立即检查最终状态。
   测试驱动使用既有模拟时钟推进时间并执行真实 poller，再运行原有协议/最终状态断言；
   不直接改状态。原始 3 个认证用例失败、3 个 PSK 用例失败，修复后均通过。

## 复现

```sh
conan create archives/s/spdk/25.05 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -c tools.build:jobs=4
```

原始上游单元测试 shell 驱动还加载 Linux 硬件测试基础设施；本配方直接运行其构建的
全部 CUnit 可执行程序。使用上游断言和模拟层，不用消费者代替上游单测。
生产 DPDK/EAL 的硬件与内核边界仍按前文申报。
