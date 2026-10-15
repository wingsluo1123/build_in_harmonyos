# DRAFT-ohos-cpu-topology-sysfs-core-siblings-list：OHOS sysfs 只暴露 `*_list` 兄弟文件，hwloc 静默退化为单 PU

- **来源**：likwid 5.5.1 适配（2026-10-13，task 8470）
- **领域**：platform / compat / detection（OHOS sysfs 与 glibc-Linux 的差异）
- **邻近但不同**：E287（fuzz/tftp 的 sysfs 用法，与 CPU 拓扑无关）；E211/E147/E094（缺
  `pthread_setaffinity_np` 等 affinity **API**，是"符号不存在"，本类是"文件不存在"）。

## 现象

在 OHOS 上用 hwloc 发现 CPU 拓扑时，**不报错、不崩溃，静默给出"单核机器"**：

```
$ /tmp/hwdiag         # 打印 hwloc_get_nbobjs_by_type()
PU=1 CORE=1 SOCKET=0 PACKAGE=0 NUMA=1
```

- `make`/`conan create` 全部成功，没有任何 error/warning。
- 设 `HWLOC_COMPONENTS=linux`、`HWLOC_FSROOT=/`、`HWLOC_THISSYSTEM=1` 都无效，仍是 `PU=1`。
- 依赖 hwloc 的上层（likwid 的 `hwloc_init_cpuInfo`）随后在
  `hwloc_get_obj_by_type(HWLOC_OBJ_SOCKET, 0) == NULL` 处报
  `Failed to read cpuinfo`（`-EFAULT`）而失败。

## 根因

OHOS/HarmonyOS 的 `/sys/devices/system/cpu/cpu0/topology/` 目录实际内容：

```
core_id  core_siblings_list  physical_package_id  thread_siblings  thread_siblings_list
```

即：有 `core_siblings_list` / `thread_siblings_list`（cpulist 文本），有 `thread_siblings`
（cpumask 十六进制），但**没有 `core_siblings`**；也没有较新内核的
`package_cpus` / `core_cpus` / `die_cpus`。

hwloc 2.9.3 的 `check_sysfs_cpu_path()` 只接受两组文件名之一：

1. `core_siblings` + `thread_siblings`（旧内核），或
2. `package_cpus` / `core_cpus`（新内核）。

OHOS 两组都不满足 → 函数返回 `-1` → `hwloc_linuxfs_look_cpu()` 打印
`failed to find sysfs cpu topology directory, aborting linux discovery` 并整体放弃
CPU 发现，回落到 `no_os` 组件 → `PU=1`。

第二个同族现象：OHOS 不会因 `physical_package_id=0` 生成 Package/Socket 对象，所以
`hwloc_get_obj_by_type(HWLOC_OBJ_SOCKET, 0) == NULL`。要求"必须有 Socket 对象"的代码会
直接失败。

**实测对照**：同一份 OHOS sysfs，外部 `hwloc/2.14.0` 报 `PU=20 CORE=10`（它放宽了文件名
判断），捆绑的 `hwloc 2.9.3` 报 `PU=1`；两者都报 `SOCKET=0/PACKAGE=0`。

## 修复（最小可移植，不改平台宏、不依赖环境变量）

1. **放宽兄弟文件名探测**：`check_sysfs_cpu_path()` 除
   `core_siblings`+`thread_siblings` 外，也接受
   `core_siblings_list`+`thread_siblings_list`。命中后仍按 `old_filenames` 读
   `thread_siblings`（OHOS 有）即可拿到 core 划分——`core_siblings` 缺失只影响
   Package 划分，不影响 PU/CORE。
2. **容忍缺少 Package/Socket**：把"必须有 Socket 对象"改成
   `SOCKET → PACKAGE → PU` 依次回退，用 PU 对象承载 CPU 身份
   （CPUModel 之类的 info 在 OHOS 上本就来自 `/proc/cpuinfo`，不在对象上）。
3. **验证口径用"PU 计数"**：补丁前 `nbobjs_by_type(PU) == 1`，补丁后 `== 20`。

## 验证

| 状态 | hwloc `nbobjs_by_type` | likwid-topology |
|---|---|---|
| 捆绑 2.9.3 未打补丁 | PU=1 CORE=1 SOCKET=0 | 失败（`Failed to read cpuinfo`） |
| 打 0002（放宽文件名） | PU=20 CORE=10 SOCKET=0 | — |
| 再打 0003（Socket→PU 回退） | PU=20 CORE=10 SOCKET=0 | `Sockets: 6` / HWThread 0..19 |

反向：删补丁后 `PU=1` 复现，证明补丁对症状敏感。

## 排查口诀

> OHOS 上 hwloc（或任何读 `/sys/devices/system/cpu/*/topology/` 的代码）**静默报告
> 单核**时，先 `ls /sys/devices/system/cpu/cpu0/topology/`：只要没有 `core_siblings`
> 而只有 `core_siblings_list`，就是本条——不是 CPU 绑定、不是 cgroup、也不是权限问题。

## 适用边界

- 适用于 OHOS 上做 CPU/缓存/NUMA 拓扑发现的库（hwloc 及基于它的 OpenMPI、性能工具）。
- 不适用于"真的只有 1 个 CPU"的场景；判据是 `PU==1` **同时** sysfs 里确实有 20 个
  `cpuN` 目录、`online=0-19`。
- Package 对象缺失是 OHOS sysfs 的客观事实，回退到 PU 即可，不必伪造 Socket。
