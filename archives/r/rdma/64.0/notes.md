# rdma 64.0 适配笔记

上游: linux-rdma/rdma-core v64.0（CMakeLists.txt: `set(PACKAGE_NAME "RDMA")` /
`set(PACKAGE_VERSION "64.0")`）
本仓归档名 `rdma`，与上游 `PACKAGE_NAME` 一致。

## 编译环境
- 构建系统: cmake (+ 上游自研 buildlib/rdma_functions.cmake)
- 编译日期: 2026-10-15
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 源码: 官方 GitHub release v64.0
#   https://github.com/linux-rdma/rdma-core/releases/download/v64.0/rdma-core-64.0.tar.gz
#   SHA-256: d170d0265e1e5030c574c8613a1fecc047413282b94c2bc4cf2e99477d82ee93
#
# 配方 configure_options（与 56.1/61.0 同口径，禁用 OHOS 上不可用的可选特性）：
cmake -S <src> -B <build> -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_RESOLVE_NEIGH=0 \
    -DNO_PYVERBS=1 \
    -DNO_MAN_PAGES=1 \
    -DENABLE_STATIC=1 \
    -DNO_COMPAT_SYMS=1 \
    -DENABLE_VALGRIND=0 \
    -DENABLE_WERROR=0 \
    -DCMAKE_INSTALL_LIBEXECDIR=libexec
ninja -C <build> && ninja -C <build> install
```

补充编译标志（配方 `generate()` 注入）:
- `-include <compat/ohos-compat.h>` —— OHOS libc 兼容层（见下）
- `-D_GNU_SOURCE` —— OHOS `<string.h>` 仅在 `_GNU_SOURCE` 下暴露 `strdupa()`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `redefinition of 'sockaddr_storage'`（`linux/socket.h` 与 `sys/socket.h` 同时命中） | OHOS musl 未定义 `__MUSL__`，`sys/socket.h` 的 `#ifndef __MUSL__` 保护未生效 | 配方注入 `-D__MUSL__=1`（OHOS 头文件中仅 `sys/socket.h` 使用该宏，影响面可控，与 56.1/61.0 同口径，E119） |
| 2 | `call to undeclared function 'strdupa'` → `-Wint-conversion` 报错（`libibverbs/dynamic_driver.c` 等） | 上游 `CMakeLists.txt:378` 只在 `HAS_CLOEXEC` 判定失败时才 `add_definitions(-D_GNU_SOURCE)`；OHOS 的 `O_CLOEXEC` 可用，故 `_GNU_SOURCE` 未注入 | 配方显式注入 `-D_GNU_SOURCE` |
| 3 | `undefined symbol: rindex`（`srp_daemon/srp_daemon.c:745`） | OHOS **链接期** sysroot 导入库不导出 BSD 遗留函数 `rindex()`（运行期 `libc.so` 中存在，`test_ohos_specific` 已实测二者结果一致） | 兼容层 `#define rindex strrchr`（语义等价）；可执行文件侧若直接引用须用弱声明，否则链接失败 |
| 4 | `getpass` 隐式声明报错（`ibdiag_common.c:286`、`ibportstate.c:554`、`saquery.c:1560/1649/1671`） | OHOS musl 的 `getpass()` 既不在头文件中声明，也不在 sysroot 导入库中导出 | 兼容层 weak 引用转发到运行期 libc 的同名符号；缺失时回退到 termios 无回显实现（E093） |
| 5 | `program_invocation_short_name` 未定义（`librdmacm/preload.c:261`） | 该符号是 glibc 专有 CRT 符号，OHOS musl 导出的是 BSD 等价物 `__progname` | 兼容层 `#define program_invocation_short_name __progname`（E493/E203） |
| 6 | `pthread_cancel/setcancelstate/setcanceltype/testcancel` 编译期未声明、链接期未导出（`ibacm/src/acm.c`、`ibacm/prov/acmp/src/acmp.c`、`librdmacm/examples/rping.c`） | OHOS 未实现 POSIX 线程取消：`<pthread.h>` 无声明、链接期 sysroot 不导出符号；运行期 `libc.so` 虽有 `pthread_cancel` 但返回 `ENOSYS`(38)，`setcancelstate` 不写回 `oldstate`（实测 `test_ohos_specific` T4 报告 `oldstate=-1`） | 兼容层补齐符号面（`pthread_cancel` 弱引用转发平台返回值、`setcancel*` 报告成功、`testcancel` 空操作）；`rping.c` 另打补丁改为 SIGUSR1 信号式线程退出 + `pthread_join`（E513） |
| 7 | `ninja install` 报 `bin/srp_daemon is not a directory` | Conan `CMakeToolchain` 把 `CMAKE_INSTALL_LIBEXECDIR` 默认设为 `bin`，与 `rdma_sbin_executable(bin/srp_daemon)` 冲突（`srp_daemon/CMakeLists.txt` 会向 `${LIBEXECDIR}/srp_daemon` 安装 `start_on_all_ports`） | 配方 `generate()` 覆盖 `CMAKE_INSTALL_LIBEXECDIR=libexec`（`tc.variables`，非 `cache_variables`） |
| 8 | 包内所有 `.so` 的 ELF dynamic 段**没有 SONAME**；`librdmacm.so` 的 `DT_NEEDED` 记录为构建树相对路径 `lib/libibverbs.so`，离开构建目录即无法加载；CI 的 L5a SONAME 门禁直接判 fail | `uname -s` 返回 `HarmonyOS` → `CMAKE_SYSTEM_NAME="HarmonyOS"`，而 CMake 4.1.2 没有 `Modules/Platform/HarmonyOS.cmake`，回落到通用平台模块；定义 SONAME 标志的 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`（在 `Platform/Linux.cmake` 中）因此为空，链接器收不到 `-Wl,-soname`（与知识库 `DRAFT-libharu-2.3.0-missing-dt-soname` 同根因） | 配方 `generate()` 恢复该标志：`tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"`；修复后 `-Wl,-soname,librdmacm.so.1` 出现在链接命令中，产物 SONAME 为相对名（L5a 通过），依赖方 `DT_NEEDED` 变为可重定位的 `libibverbs.so.1` |
| 9 | 上游 C 测试提示 `cannot open shared object file: lib/libibverbs.so` | 同 #8：`DT_NEEDED` 是相对路径，加载器按“含 `/` 的路径按字面解析”处理，只有 cwd 下正好存在 `lib/` 时才偶然成功 | 同 #8 修复；测试仍在 `<build>` 目录内执行以保持一致 |

## 源码修改

`patches/` 共 1 个补丁（`patch_generation` 见 manifest.yaml）:

- `0001-librdmacm-examples-rping.c.patch` —— `librdmacm/examples/rping.c`：
  移除 `pthread_testcancel()`，把 `pthread_cancel(cb->cqthread)` 改为
  `rping_setup_thread_exit()` + `pthread_kill(cb->cqthread, SIGUSR1)` + `pthread_join`。
  该写法把 CQ 线程的退出从「取消语义」改为「保留信号退出 + join」，在 OHOS 上可真正回收
  joinable 线程（E513），且不依赖平台宏，在 Linux 上同样成立。

其余 OHOS libc 差异全部收敛到配方级兼容层 `compat/ohos-compat.h`（不修改上游源码），
由 `generate()` 以 `-include` 强制包含进每个编译单元。

## 依赖版本

- 无外部 conan 依赖（libnl / pyverbs / man 页 / valgrind 全部禁用，见 configure_options）
- 系统库: pthread, rt, dl
- 构建期: Ninja、CMake（Conan 工具链提供）

## 验证结果

```bash
# 1) 全量构建 + 安装（配方 conan create 内部执行）
cmake --build <build> && cmake --install <build>   # rc=0

# 2) 上游 C 测试（<build>/bin 下 8 个测试可执行文件）
cd <build>
./bin/bitmap_test              # rc=0   PASS（25 条 OK 断言）
./bin/umad_compile_test        # rc=0   PASS
./bin/umad_reg2                # rc=0   PASS（无 ib_umad 模块告警）
./bin/umad_register2           # rc=0   PASS（无 ib_umad 模块告警）
./bin/ibsendtrap               # rc=255 无 ib_umad 内核模块（上游 port 打开失败即 exit(-1)）
./bin/umad_sa_mcm_rereg_test   # rc=255 无 RDMA 硬件（umad_get_port 失败）
./bin/testleaks                # rc=1   无 RDMA 硬件（can't open MAD port）
./bin/mcm_rereg_test           # rc=139 无 RDMA 硬件（打开 MAD 端口失败后上游错误路径 SIGSEGV）

# 3) test_package（消费者视角 + 鸿蒙专项，conan create 自动执行）
./test_rdma           # rc=0  PASS（断言声明 9 条，执行 7 条）
./test_ohos_specific  # rc=0  PASS（断言声明 21 条，执行 19 条）
./test_consumer       # rc=0  PASS（rc 判定，5 处有效性检查）
```

- 上游 C 测试: **8/8 全部构建并运行**；4 通过（bitmap_test / umad_compile_test / umad_reg2 /
  umad_register2），4 因 HarmonyOS PC 无 RDMA 硬件、无 `ib_umad` 内核模块而按上游自身错误路径退出
  （ibsendtrap / umad_sa_mcm_rereg_test / testleaks / mcm_rereg_test）
- `test_package`: 3/3 通过
- Python(pyverbs) 测试: 51 个测试模块 / 384 个用例，因 `NO_PYVERBS=1`（CI 无 Cython/numpy，
  见 SKILL W0b CI 能力矩阵）且全部依赖真实 RDMA 设备未实例化，源码声明数已计入台账
- `conan-verify`: G0-G4 全部 PASS（含 R26 系统同名库隔离、产物完整性）
- L5 SONAME 门禁自检: 包内 `lib/` 顶层 11 个 `lib*.so` 全部带相对 SONAME（0 缺失）
- 详见 `reports/test-report.md`

## 注意事项

- OHOS 无 RDMA 硬件：`ibv_get_device_list()` 返回 0 设备属正常（56.1/61.0 同口径）
- OHOS 未实现 POSIX 线程取消，`ibacm` 的 SA 响应线程停机路径退化为「取消请求返回失败 +
  调用方走错误分支返回」，不会阻塞 `pthread_join`；`rping` 已用信号式退出消除该依赖
- `NO_PYVERBS=1` 是本库在 CI 上的既定口径：pyverbs 需构建期 Cython + numpy，CI 仅安装
  Conan（`ci/conan/setup.sh`），无法保证；如需 pyverbs，应另立工具链依赖包后单独适配
---

**编译结束**: 2026-10-15 21:00
**最终状态**: published
