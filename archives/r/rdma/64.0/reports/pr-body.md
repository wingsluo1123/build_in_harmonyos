- **三方库名称**：rdma（上游工程名 rdma-core）
- **上游版本**：v64.0
- **上游仓库地址**：https://github.com/linux-rdma/rdma-core
- **适配路径**：路径 B（贡献创新）—— 除配方适配外，随本 PR 提交知识图谱草稿 `knowledge/drafts/E429-draft-98B5.{kv,md}`
- **使用知识库**：openharmony-compile-agent；命中/引用条目 E119（`__MUSL__` 头文件冲突）、E093（`getpass`）、E493/E203（`__progname`）、E513（POSIX 线程取消）、`DRAFT-rdma-core-61.0-conan-libexecdir-bin-collision`（LIBEXECDIR 冲突）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 8 | 来源：上游 CMake 函数 `rdma_test_executable()`（`util/tests`、`libibumad/tests`、`libibnetdisc/tests`、`infiniband-diags`），共 8 个测试可执行文件 |
| 集成测试 | 0 | 上游未提供集成测试套件 |
| 其他测试 | 51 个模块 / 384 个用例 | 来源：上游 pyverbs `tests/test_*.py`（51 个模块、384 个 `def test_`）；本次 `NO_PYVERBS=1` 未构建 pyverbs，未实例化，原因见「补充说明」 |
| **合计** | **8 个 C 测试二进制 + 51 个 Python 测试模块（384 用例）** | 上游全程未调用 `enable_testing()`，故 `ctest -N` 注册 0 条 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 8 | 不变 | 8/8 全部构建并在 OHOS aarch64 上实际运行：4 通过、4 因无 RDMA 硬件/内核模块阻塞（非适配缺陷） |
| 集成测试 | 0 | 不变 | 上游未提供 |
| 鸿蒙特有测试 | 3 | 新增 | `test_package/test.c`（声明 9 条断言，执行 7 条）、`test_ohos_specific.c`（声明 21 条断言，执行 19 条）、`test_consumer.c`（rc 判定，5 处有效性检查），全部 PASS |
| **合计** | **11** | **+3** | 11 个测试二进制在 OHOS aarch64 上执行；新增断言声明 30 条、本次执行 26 条（4 条未触达：3 条位于「有设备才进入」的逐设备循环内，1 条为 T3 的 `rindex` 存在性分支只走其一），执行项 26/26 通过，0 失败 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

本 PR 唯一的源码补丁 `patches/0001-librdmacm-examples-rping.c.patch` 修改的是上游**示例程序** `librdmacm/examples/rping.c`（不属测试用例），且补丁内不含任何平台宏；8 个上游测试二进制的源码未做任何改动，直接构建后运行。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无消费者视角用例、且未注册 ctest，适配后补全了测试

- **补全的测试范围**：以第三方消费者视角调用安装后包的公开头文件与公开 API；并覆盖 OHOS 平台特有行为（头文件共存、libc 符号面、线程退出语义、无硬件枚举）
- **补全原因**：上游测试均为库内白盒二进制，不验证「安装后能否被下游 CMake 消费者发现/链接/运行」；OHOS 平台差异（musl 符号面、无 POSIX 线程取消、无 RDMA 硬件）也需要独立回归
- **新增测试文件清单**：
  1. `test_package/test.c` — 安装后公开头 `libibverbs`/`librdmacm` 可编译链接；设备枚举 API 语义（无硬件时 0 设备，或 NULL 且 errno 置位）
  2. `test_package/test_ohos_specific.c` — 鸿蒙特有：`__MUSL__` 下 `sockaddr_storage` 与 `<linux/netlink.h>` 共存、`__progname`、`strrchr`/`rindex` 语义等价、SIGUSR1 + `pthread_join` 线程退出、无硬件枚举一致性
  3. `test_package/test_consumer.c` — 消费者用例：仅用公开头/公开 API 枚举 `ibv_get_device_list` / `rdma_get_devices` 并输出设备 name/guid

## 验证结果

- 编译状态：通过（`conan create` 成功；`conan-verify` G0-G4/L2/L4/L5 全部 PASS；W3 本地 CI exit=0）
- 上游测试用例通过率：8/8 全部执行，其中 4/8 通过（50%）；4 项阻塞均为「HarmonyOS PC 无 RDMA 硬件 / 无 `ib_umad` 内核模块」，可运行项通过率 4/4（100%）
- 新增测试用例通过率：3/3（100%）；断言级：声明 30 条，执行 26 条，26/26 通过（4 条未执行项：3 条在无 HCA 时不进入的逐设备循环内，1 条为 `rindex` 分支的另一侧）

## 补充说明

- **无 RDMA 硬件**：OHOS 上 `/dev/infiniband`、`/sys/class/infiniband` 均不存在；`ibv_get_device_list()` 返回 0 设备属预期。4 个阻塞项：`ibsendtrap`(rc=255)、`umad_sa_mcm_rereg_test`(rc=255)、`testleaks`(rc=1)、`mcm_rereg_test`(rc=139)，均在打开 UMAD 端口或发现 IB 子网时因缺硬件退出。
- **pyverbs 未构建**：`NO_PYVERBS=1`（CI 无 Cython/numpy，与已合入的 56.1/61.0 同口径）。51 个 pyverbs 模块按源码声明数登记、未实例化，不计入通过数。
- **OHOS libc 差异**：不导出 `pthread_cancel` 族、`getpass`、`rindex`、`program_invocation_short_name`；`sys/socket.h` 需 `__MUSL__`、`strdupa` 需 `_GNU_SOURCE`。以上全部收敛到 `compat/ohos-compat.h` 兼容层（`-include` 强制注入）与 `-D__MUSL__`/`-D_GNU_SOURCE`，不修改上游源码。
- **SONAME**：HarmonyOS 无对应 CMake 平台模块，SONAME 链接标志为空，导致依赖库 `DT_NEEDED` 退化为相对构建路径；配方显式补回 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`/`_CXX_FLAG`，产物 11/11 顶层 `lib*.so` 均带可重定位 SONAME。
- **安装路径**：`CMAKE_INSTALL_LIBEXECDIR=libexec`（避免与 `bin/srp_daemon` 冲突）、`SYSUSERS_DIR=lib/sysusers.d`（上游默认绝对路径 `/usr/lib/sysusers.d` 会使 `cmake --install` 失败）。
- **已知限制**：`shared` 选项对上游 `rdma_library()` 目标无效（上游无条件 `add_library(... SHARED ...)`，同时产出静态库），与已合入的 rdma-core 56.1/61.0 保持一致。
- **知识贡献（路径 B）**：`knowledge/drafts/E429-draft-98B5.{kv,md}` —— 「上游 CMake CACHE PATH 安装目标默认绝对系统目录 → Conan 前缀打包时 `cmake --install` 报 file cannot create directory」。
- **检视意见闭环**：AI Review 指出 1 项 P2（`compat/ohos-compat.h` 的 `getpass` 回退在返回前二次 `tcgetattr()`，把已关回显的设置读回 `saved`，终端 ECHO 永不恢复）与 2 项 P3（`test.c` 恒真断言、`test_ohos_specific.c` 无效 `sizeof(指针)` 断言），均已修正并重新编译验证：`have_saved` 标志只在首次 `tcgetattr()` 成功时恢复原始 termios；断言分别改为与首次枚举结果比较、取公开符号地址断言非空。修正后本文的断言计数已按实测口径更新。
