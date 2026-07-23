# hwloc 2.12.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-20
- 编译器: clang 15.0.4 / clang++
- 状态: built (conan-verify G0-G4 + L2/L4/L5 全 PASS, 本地 CI 模拟通过)
- 上游: https://download.open-mpi.org/release/hwloc/v2.12/hwloc-2.12.2.tar.gz
- SHA256: ff7d309fdff7ceddfe15c1e79eaff25f3126a134f29f44d4e85571f187a6bab8

## 编译步骤

1. `init-build` 下载解压源码到 `~/tmp/builds/hwloc-2.12.2.{orig,work}` 双轨目录
2. `perl patch-autotools-ohos.pl config/config.guess config/config.sub` 加 OHOS 平台识别
3. 手动修 `config/config.sub` 第 1836 行加 `linux-ohos*` 到 kernel-os 兼容列表
4. `sed -i 's/umask 077/umask 022/g' configure` 修 HMDFS umask 077 + mktemp -d + 重定向写入必拒陷阱
5. `./configure --prefix=$DEFAULT_PREFIX` 通过
6. `make -j2` 通过
7. `make install DESTDIR=$TEST_PREFIX` 通过
8. `hwloc-info --version` 输出 `2.12.2`，13 个 bin + libhwloc.so.15.10.1 产物完整
9. `make check` 44 个测试 42 PASS / 2 SKIP (shmem: HMDFS 共享内存限制) / 0 FAIL

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不识别鸿蒙平台 | GNU config.guess 无 OHOS 检测分支 | patch-autotools-ohos.pl + config.sub 加 linux-ohos kernel-os |
| 2 | HMDFS umask 077 + mktemp + 重定向写入被拒 | HMDFS 对 umask 077 创建的临时目录内重定向写入必拒 | 全源文件 sed umask 077→022（configure/Makefile.in/config.guess/all test scripts） |
| 3 | lstopo 探测真实硬件时 SIGSYS (Signal 31) | 鸿蒙沙箱对 4 个 NUMA mempolicy syscall 发 SIGSYS 而非 ENOSYS | configure 运行能力探测；仅定义 `HWLOC_HAVE_WORKING_LINUX_MEMPOLICY` 时调用 syscall，否则返回 ENOSYS |
| 4 | hwloc_get_last_cpu_location + glibc-sched 测试 assert 失败 | 鸿蒙 sched_setaffinity 静默成功不绑定 (rc=0 但 sched_getaffinity 返回全 CPU) | 运行时用 sched_getaffinity 回读验证；不一致时库返回 ENOSYS、测试返回 automake SKIP(77) |
| 5 | freebsd ports 测试编译错误 `__int32_t` 未定义 | 鸿蒙 sysroot 不提供 `__int32_t` (双下划线 BSD 内部类型) | freebsd/sys/user.h `__int32_t` → `int32_t` (标准 POSIX 类型) |
| 6 | conan create 失败 `config.status: ./confggFmPm/subs1.awk: Permission denied` | config.status 固有 umask 077 + mktemp -d + 重定向写入 awk 脚本，HMDFS 必拒 | 同 #2，全局 umask 077→022 补丁覆盖 configure 内嵌的 config.status 生成器 |
| 7 | conan 2.30 官方版不接受 os=OHOS | 需 OHOS 适配版 conan 2.29.1 + settings.yml 加 OHOS 枚举 | 装社区源 conan 2.29.1 (--no-deps)，依赖用官方 PyPI 装；手动往 ~/.conan2/settings.yml 的 os: 节加 OHOS 枚举 |

## 源码修改

21 个 per-file 补丁由 `refresh-patch --auto` 生成：
- `0001`–`0005`：Makefile/config.guess/config.sub/Autoconf NUMA 能力探测及预生成 configure
- `0006`–`0008`：topology-linux 功能宏与 affinity 回读验证、config 宏模板、glibc-sched 运行时 SKIP
- `0009`：freebsd ports user.h `__int32_t` → `int32_t`
- `0010`–`0021`：测试脚本模板的 HMDFS `umask 077` → `umask 022` 兼容修改

## 依赖版本

无强依赖。可选依赖 (libxml2/cairo/ncurses) 均未启用，hwloc 用内置 backends。

## 验证结果

```bash
# 编译验证
$ hwloc-info --version
hwloc-info 2.12.2
$ lstopo --version
lstopo 2.12.2

# make check 结果
# TOTAL: 44
# PASS:  42
# SKIP:  2 (shmem: HMDFS 共享内存限制；glibc-sched: affinity 运行时能力不可用)
# FAIL:  0

# conan-verify (8 道门禁全 PASS)
G0 预构建风险评估: PASS
G1 配方完整性: PASS
G2 conan create (干净构建): PASS
G3 系统同名库隔离 (R26): PASS
G4 产物完整性: PASS
L2 平台功能矩阵 (smoke test): PASS
L4 静态安全扫描 (NX·PIE·RELRO): PASS
L5 产物基线对比: PASS

# 本地 CI 模拟 (build_and_test.sh)
L0a-L0h 质量门禁: 全 PASS
conan create: RC=0
L1a test_package 执行: PASS
L1b 测试编译运行痕迹: PASS
L1c 测试输出含被测包标识 (R34): PASS (输出 "hwloc 2.12.2 OK: topology depth=3")
L4 安全扫描: PASS (BIND_NOW+PIE)
L5 产物基线: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 1.4KB | Conan 配方 (autotools, 静态库) |
| conandata.yml | 1.2KB | 源码 + 6 个补丁声明 |
| test_package/test.c | 1.4KB | L1 测试 (调用 hwloc_topology_init/load/get_depth 验证 API) |
| test_package/conanfile.py | 0.8KB | L1 测试配方 (CMake) |
| test_package/CMakeLists.txt | 0.3KB | CMake 配置 |
| test_package/MANIFEST.yml | 3.0KB | 上游 44 个测试声明 |
| commands.json | 0.3KB | 命令行工具声明 (R38, 13 个 bin) |
| patches/0001-*.patch ~ 0006-*.patch | 共 11KB | 6 个适配补丁 |

## 注意事项

1. **HMDFS umask 077 陷阱**：鸿蒙 HMDFS 对 `umask 077` + `mktemp -d` 创建的目录内重定向写入必拒（非间歇性 race，是必现）。所有 autotools 生成文件（configure/Makefile.in/config.guess/所有测试脚本）含 `umask 077` 都需改 `umask 022`。
2. **鸿蒙沙箱 SIGSYS 行为**：4 个 NUMA mempolicy syscall (`set_mempolicy`/`get_mempolicy`/`migrate_pages`/`move_pages`) 在鸿蒙沙箱里直接发 SIGSYS 而非返回 ENOSYS。hwloc 需加 `#ifdef __OHOS__` 守卫提前返回 ENOSYS。
3. **鸿蒙 sched_setaffinity 静默成功 bug**：`sched_setaffinity()` 返回 rc=0 声称成功但不实际绑定，`sched_getaffinity()` 仍返回全部 CPU。hwloc 需加 `#ifdef __OHOS__` 守卫返回 ENOSYS 避免下游误解绑定状态。
4. **conan 必须用 OHOS 适配版**：官方 conan 2.30 不接受 `os=OHOS`。社区源提供 conan 2.29.1 适配版（需 `--no-deps` 装，依赖用官方 PyPI 装），settings.yml 需手动加 OHOS 枚举。
5. **下游可硬依赖 hwloc/2.12.2**：libhwloc.so 库本身完全正常（`-i synthetic` 拓扑生成成功），CPU 亲和性绑定是鸿蒙沙箱限制非 hwloc 缺陷。下游 `self.requires("hwloc/2.12.2")` 能拿到完整库 + 13 个命令行工具。
---

**编译结束**: 2026-07-21 00:39
**最终状态**: built
