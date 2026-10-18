# sg3_utils 1.49 — 鸿蒙 PC 适配笔记

## 1. 结论速览

| 项 | 结果 |
|---|---|
| 构建系统 | 上游自带 **CMake**（1.44 起双构建系统） |
| 源码 | 官方 GitHub tag `release-1.49`（官网 https 证书 2026-10-01 过期） |
| 源码补丁 | 1 个：`0001-CMakeLists.txt.patch`（平台判定，非桩） |
| 产物 | 84 个可执行文件（72 个 `sg_*` 工具 + 12 个历史别名/脚本如 `sginfo`、`sgm_dd`、`rescan-scsi-bus.sh`）+ `libsgutils2.a` + 19 个头文件（`include/scsi/`） |
| 静态库 | `libsgutils2.a`（上游名 `libsgutils2-1.49.a`，已归一） |
| conan create | 通过（test_package 9 项断言 + 5 个 CLI 实测） |

## 2. 关键问题：CMake 平台判定把 HarmonyOS 降级成 PT_DUMMY

上游 `CMakeLists.txt` 用 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 判定 Linux 专属的
pass-through（PT）实现分支，HarmonyOS 上条件不成立 → 落入 fallback `PT_DUMMY` 分支。

后果是**静默功能降级**，编译本身不报错：

- 所有 PT 代码编成 dummy（`sg_pt_*` 空转，读写命令不下发）；
- `src/CMakeLists.txt` 的 `if (SG_LIB_LINUX AND NOT PT_DUMMY)` 分支整体不构建。
  该分支包含变量 `SG3_UTILS_LINUX_ONLY` 的 **13 个工具**
  （`sg_copy_results` `sg_dd` `sg_emc_trespass` `sginfo` `sgm_dd` `sg_map` `sg_map26`
  `sgp_dd` `sg_rbuf` `sg_read` `sg_reset` `sg_test_rwbuf` `sg_xcopy`）**加 `sg_scan`，共 14 个**。

**修复**（补丁 0001）：把 HarmonyOS/OHOS 并入 Linux 分支。

```cmake
-elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux")
+elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
```

这不是打桩（R40）：OHOS sysroot 实测具备 `scsi/sg.h`、`linux/bsg.h`、
`linux/nvme_ioctl.h`、`linux/major.h`、`linux/types.h`、`linux/kdev_t.h`，
sg v4 与 bsg 的真实 PT 可正常编译链接。实测 `LINUX_ONLY` 的 14 个工具全部构建产出。
回归保护写进 test_package：`sg_dd --version`、`sg_copy_results --version` 必须可执行——
降级分支下这两个二进制不存在。

## 3. 为什么用 CMake 而不是 Autotools

官方 GitHub tag 归档是 git 检出，**不含预生成 `configure`**；构建机与 CI 均无
automake/libtool，无法 `autoreconf`。上游 1.44 起同时维护 Autotools 与 CMake，
CMake 侧功能等价（真实 PT 分支已按上节修复），故选 CMake。

## 4. 静态库安装的坑

上游 `lib/CMakeLists.txt`：

```cmake
set_target_properties(sgutils2 PROPERTIES OUTPUT_NAME "sgutils2-${PROJECT_VERSION}" ...)
install(TARGETS sgutils2 EXPORT sgutils2Targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR} ...)   # 没有 ARCHIVE DESTINATION
```

两个结果：
1. 库名内嵌版本 → `libsgutils2-1.49.a`（下游 `-lsgutils2` 解析不到）；
2. 静态库属 ARCHIVE 产物，未声明 `ARCHIVE DESTINATION` → **根本不安装**（`cmake --install` 后 lib 目录为空）。

配方在 `package()` 里从构建目录补齐并归一为 `libsgutils2.a`；静态构建下上游仍会无条件
创建指向 `.so` 的开发符号链接（悬空），一并删除。

## 5. 上游测试实测（R51）

上游测试套件在 `ttesting/`，由独立 Makefile 构建，未接入 CMake 或 `make check`
（顶层无 check 目标、无 ctest 注册）。清点口径 = `ttesting/Makefile` 的 `EXECS` 变量：
**20 个测试程序 = 12 个 `.c` + 8 个 `.cpp`**（目录内另有 `sg_json_builder_test.c`、
`sg_scat_gath.cpp` 等示例，不在 `EXECS` 内，不计入）。

| # | 测试 | 结果 |
|---|---|---|
| 1 | `sg_sense_test.c` — fixed 格式 sense 解码 | ✅ 实跑通过 |
| 2 | `tst_sg_lib.c` — 9 个断言选项（`-s -e -u -p -H -b16 -b32 -b64 -B5`） | ✅ 实跑通过 |
| 3 | `sg_tst_json_builder.c` — JSON 构建 | ✅ 实跑通过 |
| 4 | `sgs_dd.c` — 文件模式 dd（`bs=512 count=4`） | ✅ 实跑通过 |
| 5 | `sg_chk_asc.c` — ASC/ASCQ 与 t10.org `asc-num.txt` 比对 | ⚠️ 数据漂移（1.49 码表较旧；纯码表内容比对，不涉及平台相关代码） |
| 6 | `sg_chk_inq_vd.c` — 与 t10.org `stds-num.txt` 比对 | ⚠️ 数据漂移（同上） |
| 7-20 | `sg_queue_tst` `bsg_queue_tst` `sg_tst_nvme` `sg_tst_ioctl` `sg_tst_bidi` `sg_tst_excl` `sg_tst_excl2` `sg_tst_excl3` `sg_tst_context` `sg_tst_async` `sg_iovec_tst` `sgh_dd` `sg_mrq_dd` `sg_take_snap` | ⏭ 缺设备无法运行（均需 `/dev/sg*`、`/dev/bsg` 或 `/dev/nvme*`；构建机与鸿蒙 PC 均无此节点） |

汇总：**20 = 4 实跑通过 + 2 数据漂移 + 14 缺设备**；
通过率 **4/20 = 20%**，排除 14 项缺设备后的可运行项 **6 项中 4 项通过 = 66.7%**。
20 个测试程序全部编译链接通过（C++ 测试上游用 `-std=c++23`，OHOS clang 15 最高 `c++20`，
实测 c++20 可编译运行——兼容性差异记录，不阻塞）。

复现命令（实测逐文件编译，未走 `ttesting/Makefile`——其 LD 固定 g++、且依赖 autotools 树内
`../lib/*.o`，CMake 构建下不可用）：

```bash
# C 用例
clang -std=c99 -DSG_LIB_LINUX -DHAVE_NVME -I include ttesting/<t>.c libsgutils2.a -lpthread -o <out>
# C++ 用例（sg_mrq_dd 需追加 sg_scat_gath.cpp）
clang++ -std=c++20 -DSG_LIB_LINUX -DHAVE_NVME -I include ttesting/<t>.cpp libsgutils2.a -lpthread -o <out>
```

**R40 人工确认项**：本包属系统底层（SCSI pass-through），当前证据覆盖编译链接、真实 PT 代码路径
与无设备的解码/码表逻辑；真实 `SG_IO`/bsg ioctl 的运行时行为尚未验证（构建机与鸿蒙 PC 均无
`/dev/sg*` / `/dev/bsg`）。需在具备 SCSI 设备的鸿蒙 PC 上跑 `sg_inq`/`sg_vpd`/`sg_turs` 并附输出
作为最终确认。

**补鸿蒙独有测试**（上游用例在无设备环境只能覆盖解码/码表，见 `test_package/`）：

- `test.c`（5 断言）：`sg_lib_version()` 格式、ASC/ASCQ 码表（0x24/0x00、0x29/0x00）、
  fixed 格式 sense 解码、`hex2str` 格式；
- `ohos_test.c`（4 断言）：**描述符格式 sense(0x72) 解码**（依赖 `struct sg_scsi_sense_hdr`
  位域布局与描述符链遍历，交叉编译/字节序问题会直接暴露）、fixed 格式 NOT READY 解码、
  `sg_err_category_sense` → 类别串映射、空 sense 边界不崩溃；
- `conanfile.py test()`：`sg_inq`/`sg_vpd`/`sg_turs --version` 可执行性自检（RC=0；打印各自版本，非包版本），
  以及 `sg_dd`/`sg_copy_results --version` ——**真实 PT 分支的回归守门**。

## 6. 依赖检查（W0）

`requirements()` 为空：sg3_utils 只依赖 libc + pthread，无第三方库依赖。
下游使用者：`lsvpd`（依赖 `libsgutils2`）。本归档同时提供库与 CLI 工具，
软件级 `commands.json` 已声明 tool 类型（R38）。

## 7. 复现命令

```bash
conan create archives/s/sg3_utils/1.49 \
  --profile:build=ohos-aarch64 --profile:host=ohos-aarch64 \
  -o "&:shared=False"
```

共享库形态可用 `-o "&:shared=True"`（`libsgutils2.so` + `libsgutils2-1.49.so.2`）。
---

**编译结束**: 2026-10-17 18:39
**最终状态**: built
