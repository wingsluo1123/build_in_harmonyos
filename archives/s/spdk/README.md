# spdk

SPDK（Storage Performance Development Kit）是一套用 C 编写的高性能存储用户态框架：
以轮询（polled-mode）、异步、无锁方式驱动 NVMe / virtio / AIO 等块设备，并在此之上
提供 bdev、blob、blobfs、lvol、iSCSI target、NVMe-oF（nvmf）target、vhost 等服务与
库，外加以 JSON-RPC 暴露的 RPC 配置接口。全部库都建立在 DPDK 的 EAL 环境抽象之上。

- 上游：<https://github.com/spdk/spdk>（tag `v25.05`）
- 许可：BSD-3-Clause

## OHOS 适配

- **构建系统**: SPDK 自带 `./configure` + `make`；DPDK 用 meson/ninja。clang 15 /
  OHOS 6.0 aarch64，主机三元组 `aarch64-unknown-linux-ohos`。
- **捆绑 DPDK**: 上游 tarball 不含子模块。`source()` 下载 v25.05 tag 锁定的
  `spdk/dpdk@cf36799`（25.03.0）源码，配方先用 meson 交叉构建到私有前缀，
  再以 `--with-dpdk=<prefix>` 交给 SPDK `configure`。
- **原生 TLS（关键）**: OHOS clang 默认 `-femulated-tls`（`__emutls_v.*`）。DPDK 的
  每核变量通过 version script 导出，而 emutls 控制符号不在脚本里 → 其他 `.so` 链接
  报 `undefined symbol: __emutls_v.per_lcore_rte_errno`。DPDK 与 SPDK 统一加
  `-fno-emulated-tls`（OHOS 运行时支持原生 TLS，实测线程局部变量正常）。
- **sockaddr_storage 重定义（E091/E119）**: OHOS `<linux/socket.h>` 与 `<sys/socket.h>`
  都定义 `struct sockaddr_storage`。在 DPDK `eal_dev.c`/`vhost.h`、SPDK
  `pci_event.c` 的 `<linux/netlink.h>`/`<linux/if.h>` 包含处局部重命名 UAPI 类型，并在包含后 `#undef`。
- **bionic libc 缺口**: 无 `pthread_cancel` / `pthread_setaffinity_np` /
  `pthread_getaffinity_np` / glibc 的 `program_invocation_short_name`。线程改为有限等待 + 协作退出 + join 后释放资源；affinity 使用 Meson
  特性探测选择 pthread 或 `sched_*affinity`+`pthread_gettid_np`；进程名使用
  `argv[0]` basename。补丁不添加平台条件宏。
- **ISA-L**: 依赖 GNU `as` ≥ 2.24 的汇编，OHOS 无此汇编器。补丁令 `configure` 仅在
  `sysname == Linux` 时启用 ISA-L（非 Linux 直接关闭，压缩/加密软件后端随之关闭）。
- **其它**: `bdev_aio` 缺 `FALLOC_FL_*`（`#include <linux/falloc.h>`）；DPDK
  `pmdinfogen` 需要 PATH 上的 `ar`（提供 `ar → llvm-ar` shim）；HMDFS 不支持 make
  jobserver 的 FIFO（`make --jobserver-style=pipe`）。
- **运行边界（如实申报）**: DPDK EAL 需要 hugepage / vfio / uio / `/sys` 等 OHOS
  不提供的私有内核接口，SPDK 的存储数据面无法在 OHOS 上实跑。因此默认对外暴露的是
  不依赖 EAL 运行时的 CPU-only 库（`spdk_util` / `spdk_log` / `spdk_json`）；
  其余全部库仍照常编译并打包。

## 依赖

PMD 元数据生成通过 Meson 使用交叉文件配置的绝对 archiver 路径，适配子进程
重设 PATH 的运行环境；构建环境先应用 Conan profile，再应用本包工具覆盖项。

| 依赖 | 版本 | 用途 |
|------|------|------|
| openssl | 3.5.6.1 | `spdk_md5`（EVP 接口，25.05 起为硬依赖） |
| libuuid | 2.42.2 | `lib/util` 的 UUID 与 `uuid_generate_sha1` |
| libaio | 0.3.112.1 | `bdev_aio` 模块（Linux 原生 AIO） |
| pyelftools | 0.33 | 构建期：DPDK `pmdinfogen`（ELF PMD 元数据） |
| cunit | 2.1-3 | 仅测试期：运行上游 CUnit 单测 |

## 产物

| 路径 | 说明 |
|------|------|
| `include/spdk/**` | SPDK 公共头（96 个，含生成的 `config.h`/`version.h`） |
| `include/*.h` | 捆绑 DPDK 25.03.0 头文件 |
| `lib/libspdk_*.a` | 67 个 SPDK 静态库（不安装测试支持库） |
| `lib/librte_*.a` | 60 个 DPDK 静态库 |

## 上游测试

配方构建并直接运行 103 个上游 CUnit 程序：1635 个配置内用例全部通过。
相同配置基线为 1636，1 个依赖关闭的 ISA-L crypto 后端的 DIX 加密序列未注册，
基线覆盖 1635/1636（99.94%）；另 19 个关闭的可选模块测试程序单列披露。
源码中 1376 处 CU_ADD_TEST 与 8 处 CU_add_test 是注册位置，参数化套件会展开。
消费者独立验证 6 项 CRC/Base64 行为。详见 [适配笔记](25.05/notes.md)。
