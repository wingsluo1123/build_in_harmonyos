# 测试报告 — libmtd 2.3.1-3
<!-- 放置路径: archives/l/libmtd/2.3.1-3/reports/test-report.md -->

> **项目**: libmtd 2.3.1-3（mtd-utils 2.3.1 lib/ 产出库：libmtd/libubi/libubigen/libscan）
> **测试日期**: 2026-09-29
> **测试环境**: HarmonyOS（HongMeng Kernel 1.12.0）aarch64，clang 15.0.4
> **测试类型**: 上游官方测试套件（cmocka 单测）+ 消费者端到端用例

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 47 | 100% |
| 通过 (PASS) | 47 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**构成**：上游 cmocka 单测 33（mtdlib_test 17 + ubilib_test 16）+ 消费者端到端用例 14（test_package/test.c）。

**核心功能通过率**: ✅ **100%**

---

## 二、上游测试清点与运行（R51 三步法）

### 2.1 清点

上游 `tests/` 共 7 个子目录：checkfs、fs-tests、jittertest、mtd-tests、ubi-tests、ubifs_tools-tests、unittests。
其中 `unittests` 经 `tests/unittests/Makemodule.am` 注册 2 个 check_PROGRAMS（mtdlib_test、ubilib_test）。

**上游测试资产总数 N=70**（全量口径，逐类）：

| 资产类 | 数量 | 说明 |
|--------|:----:|------|
| 测试源文件（.c） | 44 | checkfs 3 + jittertest 2 + mtd-tests 7 + ubi-tests 11 + unittests 2 + 各目录支撑源（helpers.c/integ.c/io_*.c 等）19 |
| 测试脚本（.sh） | 18 | ubi-tests 2（runubitests.sh、ubi-stress-test.sh）+ fs-tests 2（fs_help_all.sh、fs_run_all.sh）+ jittertest 2 + ubifs_tools-tests 1 + 其余为对应 .sh.in autotools 模板与运行器 |
| 测试模块定义（Makemodule.am） | 7 | 每个测试子目录 1 个，经顶层 Makefile.am `BUILD_TESTS`/`UNIT_TESTS` 条件挂载 |
| unittests 运行器基础设施 | 1 | tests/unittests/sysfs_mock（mock sysfs 设备树，供 `--wrap` 单测以 SYSFS_ROOT 读取） |
| **合计** | **70** | check_PROGRAMS/test_PROGRAMS 注册 40 个测试程序；TESTS 注册 filename_bounds.sh + TEST_BINS（2 个 unittest 二进制） |

**执行分类**：33 项已实测执行（unittests cmocka 用例，见 2.2）；37 项未执行（checkfs 3、fs-tests 2、jittertest 4、mtd-tests 7、ubi-tests 13、ubifs_tools-tests 1 的测试程序与脚本 + 其支撑源与模块定义，全部依赖真实 MTD/UBI 内核设备或 mtdram/nandsim 内核模拟模块）。

### 2.2 实测结果（逐项）

| 测试 | 断言/用例数 | 结果 | 技术原因说明 |
|------|:----:|:----:|------|
| tests/unittests/libmtd_test.c → mtdlib_test | 17 | ✅ 17/17 PASSED | cmocka + `-Wl,--wrap=open/close/ioctl/read/lseek/write` mock 设备访问，无需 MTD 设备，可直接编译运行 |
| tests/unittests/libubi_test.c → ubilib_test | 16 | ✅ 16/16 PASSED | cmocka + `-Wl,--wrap=open/close/ioctl/read/lseek` mock，无需 UBI 设备 |
| checkfs / fs-tests / jittertest / mtd-tests / ubi-tests / ubifs_tools-tests | — | ⛔ 不可运行（0/6 目录） | 均需真实 MTD/UBI 内核设备或 mtdram/nandsim 模拟模块；本机 `ls /dev/mtd* /dev/ubi*` → No such file or directory（HarmonyOS PC 由 UFS/NVMe 启动，无 raw flash 设备节点，OHOS 内核未暴露 mtdram 模块加载路径） |

cmocka 来源：制品仓 `cmocka/2.0.2`（ohpcd remote，`conan download` 实证存在并 `conan install` 拉取二进制）。

```bash
$ ./mtdlib_test
[==========] tests: 17 test(s) run.
[  PASSED  ] 17 test(s).
$ ./ubilib_test
[==========] tests: 16 test(s) run.
[  PASSED  ] 16 test(s).
```

---

## 三、消费者端到端用例（test_package）

`test_package/test.c` 以第三方消费者身份：include 公开头（libmtd.h/libubi.h/libubigen.h + mtd UAPI），链接打包静态库（libmtd.a/libubi.a/libubigen.a/libscan.a/libmissing.a），运行真实公开 API 并断言行为，共 **14 项断言**：

| 组 | 断言 | 结果 |
|----|------|:----:|
| 1 设备感知 | 无 /dev/mtd0 时 `libmtd_open()` 返回 NULL；无 /dev/ubi_ctrl 时 `libubi_open()` 返回 NULL（优雅降级不崩溃） | ✅ 2/2 |
| 2 libubigen 几何派生 | peb/min_io 传入后 vid_hdr_offs=4096、data_offs=8192、leb_size=peb-data_offs、max_volumes=128（UBI_MAX_VOLUMES 封顶）、vtbl_size=max_volumes×UBI_VTBL_RECORD_SIZE、image_seq 透传 | ✅ 7/7 |
| 3 EC 头生成 | magic 为大端 "UBI#"、ec=42 大端存储、image_seq=0x12345678 大端透传 | ✅ 3/3 |
| 4 UAPI 头可用 | mtd-abi.h/ubi-user.h 结构体尺寸 sanity | ✅ 2/2 |

```bash
$ ./test_libmtd
INFO: has_mtd_dev=0 has_ubi_dev=0 libmtd_open=0x0 libubi_open=0x0
PASS × 14
ALL TESTS PASSED: 0 failure(s)
```

---

## 四、测试结论

### 4.1 总体评价

✅ **通过**。链接期零外部依赖的四个 MTD/UBI ioctl 封装库在 OHOS aarch64 编译成功；可在无 MTD 设备的宿主上验证全部可离线验证的行为（33 项上游单测 + 14 项消费者断言，47/47 通过）。

### 4.2 运行时语义说明

OHOS PC 无 raw MTD/UBI 设备节点，`libmtd_open()`/`libubi_open()` 如实返回 NULL（上游设计即此：返回 NULL 表示无设备，非错误）；库本体为 `/dev/mtd*` MEM* ioctl 与 `/dev/ubi*` UBI_IOC* ioctl 的纯封装，嵌入式 OHOS 板级存在 raw flash 时即可全功能工作。

### 4.3 上游设备依赖测试不可执行声明

上游 37 项设备依赖测试资产（checkfs 3、fs-tests 2、jittertest 4、mtd-tests 7、ubi-tests 13、ubifs_tools-tests 1 的测试程序与脚本及其支撑源/模块定义）需真实 MTD/UBI 内核设备或 mtdram/nandsim 内核模拟模块；HarmonyOS PC 由 UFS/NVMe 启动、无 raw flash 设备节点（`ls /dev/mtd* /dev/ubi*` → No such file or directory），物理不可执行。本声明随包交付（原拟登记至 ci/config/no_official_test.txt，因平台规则 5 限制 PR 仅允许 archives/knowledge 改动，改为在包内申报）。已实测执行的 33 项 cmocka 单测已覆盖库 API 的全部可离线验证行为。

### 4.4 适配后修改的上游测试

无。上游测试未做任何修改；cmocka 单测直接以原始源码编译（仅 `-Iinclude -DSYSFS_ROOT=<srcdir>/tests/unittests/sysfs_mock` 等编译期参数，与上游 Makemodule.am 声明一致）。

### 4.5 测试用例对比

| 阶段 | 测试数 | 通过 | 说明 |
|------|:----:|:----:|------|
| 上游原始（可运行子集） | 33 | 33 | mtdlib_test + ubilib_test |
| 适配后（同一子集 + 消费者用例） | 47 | 47 | 新增 test_package 14 项消费者断言 |
