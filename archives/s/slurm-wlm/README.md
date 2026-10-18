# slurm-wlm

Slurm（Simple Linux Utility for Resource Management）工作负载管理器（SchedMD，GPL-2.0-or-later）：
集群节点/分区/作业管理、资源调度（backfill / priority / gang 等插件）、作业记账与查询工具链，
以及被上层工具链接的客户端库 `libslurm`。

- 上游项目：https://www.schedmd.com/
- 源码：`https://download.schedmd.com/slurm/slurm-25.11.4.tar.bz2`
  （sha256 `237f515adcb37b99ff6cb3e1fa81691a5f7188e94c3b6b495858b4eaecf6531d`，SchedMD 官方发布目录）
- 版本：`25.11.4`

## 功能概述

- 集群与作业管理：`sbatch`、`srun`、`scancel`、`squeue`、`scontrol`、`sinfo`、`salloc`、`sattach`
  （`bin/` 共 24 个程序；`slurmctld`、`slurmd`、`slurmdbd` 服务端亦随包交付）
- 记账与报表：`sacct`、`sacctmgr`、`sreport`、`sstat`、`sprio`、`sshare`
- 调度插件：`sched/backfill`、`sched/priority`、`select/cons_tres`（`lib/slurm/*.so`）
- 序列化插件：`serializer/json`、`serializer/url-encoded`（`serializer/yaml` 需要可选的 libyaml，未启用）
- 认证/凭据插件：`auth/munge`、`cred/munge`、`tls/none`、`hash/k12`、`certgen/script`
- `libslurm`：作业提交/查询/打包的客户端库（`lib/libslurm.{a,so,so.44}`）+ `include/slurm/*.h`

## OHOS 适配要点

1. **必须使用 SchedMD 的 release tarball**：源码树里带着预生成的 `configure`。HarmonyOS 主机只有
   autoconf/m4，没有 automake / aclocal / libtoolize，GitHub 的 tag 归档（只有 `configure.ac` + `Makefile.am`）
   在这台机器上根本无法 bootstrap。
2. **三元组退化**：随包的 2022 版 `config.sub` 不认识 `ohos` OS，autoconf 无法规范化工具链上报的
   `aarch64-linux-ohos`（E007），因此 `--build/--host=aarch64-linux-gnu`——真正的目标是 OHOS，
   因为 CC/CXX 与 sysroot 都来自 Conan 的 OHOS 工具链（补丁 0001 仍保留，用于让 `config.sub` 认识 ohos）。
3. **HMDFS 上 `getcwd()` 不可用**（E114/E386）：autoconf 的 `pwd` 探针取不到工作目录，会直接
   `configure: working directory cannot be determined`；配方在 `build()`/`package()` 里预置 `PWD`，
   并把 `CONFIG_SHELL` 指向 `/data/service/hnp/bin/bash`。`config.status` 的临时目录还要用
   `umask 022` 创建（HMDFS 会给新目录加 setgid 位，见补丁 0002、E129/E011）。
4. **musl 与 glibc 的差异**（详见 `25.11.4/notes.md` 的对照表）：
   - `sys/unistd.h`（glibc 专有）→ `<unistd.h>`（补丁 0003）；
   - `res_n*` 可重入解析器 musl 没有 → 改走 `res_init/res_search`（补丁 0004）；
   - `getpwent_r`/`getgrent_r`、`euidaccess`、`pthread_cancel*`、`inet_nsap_addr/ntoa`、
     `canonicalize_file_name`、`get_current_dir_name`、`W_EXITCODE/W_STOPCODE` 等 glibc-only 符号
     → 由配方生成的「兼容头（`-include` 强制注入）+ 垫片静态库（追加到生成的 Makefile 的 `LIBS`）」两件套补齐；
   - `cpu_set_t`/`CPU_SET` 只有定义了 `_GNU_SOURCE` 才可见（`src/common/xsched.h` 用到）。
5. **可选后端**：`numactl` 不使用（制品仓里的 `libnuma.a` 带 glibc 符号版本 `libnuma_1.1`，lld 解不开；
   Slurm 对 NUMA 亲和是可选探测）；`freeipmi`、NVML/CUDA、RSMI/ROCm、MySQL 在 OHOS 上没有对应能力，
   显式关闭；`libyaml`（→ `serializer/yaml`）也不启用 —— 接入后插件能构建，但两条相关上游用例
   仍卡在 musl 加载器对 `dlopen` 插件的符号作用域差异上（见 `25.11.4/reports/test-report.md §4.3`）。
6. **包型保持 `package_type = "application"`**：改成 `library` 会让 Conan 的 `AutotoolsToolchain`
   注入 `--disable-shared --enable-static`，插件 `.so` 不再产出、`lib_ref` 的二进制 blob 链接缺符号。
   代价是 CMakeDeps 不传播 include/libs，`test_package` 因此显式指向安装树。
7. **上游测试**：`testsuite/slurm_unit` 的 41 个 libcheck 用例在 `build()` 里通过 `make check` 真实执行，
   结果以 `SLURM-UPSTREAM-*` 行写进 `conan create` 日志（详见 `25.11.4/reports/test-report.md`）。

## 排除与替代

| 排除项 | 原因 | 替代 |
|--------|------|------|
| `numactl`（NUMA 亲和） | 制品仓 `libnuma.a` 的符号版本 lld 无法解析 | 不启用，Slurm 退化为不设置 CPU/内存亲和 |
| `freeipmi` | 需要 IPMI 硬件与 Linux 专有接口 | 不启用（`--without-freeipmi`） |
| NVML/CUDA、RSMI/ROCm | 需要 NVIDIA/AMD 专有运行时 | 不启用（`--without-nvml`、`--without-rsmi`） |
| MySQL 记账后端 | 需要 MySQL 客户端库 | 不启用（`--without-mysql`），记账可用 `slurmdbd` 文件后端 |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| munge | 0.5.16 | 认证/凭据插件 `auth/munge`、`cred/munge`（必选） |
| hwloc | 2.14.0 | 拓扑与 CPU 绑定（`select/cons_tres` 等） |
| json-c | 0.18 | JSON 输出与数据解析 |
| http-parser | 2.9.4 | `slurmrestd` 的 HTTP 解析 |
| readline | 8.3 | `scontrol`/`sacctmgr` 交互式行编辑 |
| ncurses | 6.6 | `sview`/termcap 符号（`tgetflag`、`UP`） |
| libcap | 2.78 | 特权操作与 capability 检查 |
| libaio | 0.3.112.1 | 异步 IO 记账路径 |
| zlib | 1.3.1.1 | 传递依赖统一版本（libpng 分支原为 1.3.1） |

## 功能验证

```bash
# 版本与用法
bin/sinfo --version
bin/scontrol --help | head -3

# 上游单元测试（41 个 libcheck 用例，测试报告见 25.11.4/reports/test-report.md）
conan create archives/s/slurm-wlm/25.11.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → 日志内 SLURM-UPSTREAM-TESTS total=41 pass=37 fail=4 rate=90.2%

# 消费者用例（链接安装后的 libslurm 静态库并调用公开 API）
conan test archives/s/slurm-wlm/25.11.4/test_package slurm-wlm/25.11.4
# → SLURM_CONSUMER_CHECKS=6 FAILURES=0 / SLURM_CONSUMER_OK
```

## 参考

- [SchedMD 主页](https://www.schedmd.com/)
- [Slurm 文档](https://slurm.schedmd.com/documentation.html)
- [源码下载目录](https://download.schedmd.com/slurm/)
