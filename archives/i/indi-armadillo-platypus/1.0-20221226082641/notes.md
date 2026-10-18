# indi-armadillo-platypus 1.0-20221226082641 适配笔记

## 编译环境
- **类型**: CMake 构建的 INDI 驱动**集** —— 一个工程产出 6 个可执行文件 + 1 个 INDI XML（+ Linux 下的 udev 规则）
- **驱动清单**: `indi_seletek_rotator`、`indi_dragonfly_dome`、`indi_dragonfly`、`indi_beaver_dome`、`indi_armadillo_focus`、`indi_platypus_focus`
- **编译日期**: 2026-10-07
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: `libindi/2.2.2.1` + `libnova/0.16`（均已合入，`conan install` 实测可解析）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/i/indi-armadillo-platypus/1.0-20221226082641 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 indi-3rdparty 单体仓归档（commit `945fbe12d13f3472643931e24e444a4ca69d4ed5`，
sha256 `6dee1f35…d87a`），`strip_root=True` 保留整棵仓库树——该子目录 CMakeLists 会把
`../cmake_modules` 追加进 `CMAKE_MODULE_PATH`（`include(CMakeCommon)` 与
`find_package(INDI)` 都依赖它）。比赛版本号 `1.0-20221226082641` 是 Debian 打包日期戳；
源码代次对齐到 v2.2.2 代 commit（该 commit 树内确实含本驱动目录），与同快照兄弟驱动
indi-aok / indi-talon6 / indi-maxdomeii **同一 commit 与同一 sha256**。

### 2. 配置（generate()）
- **`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`**：CMake 无 HarmonyOS
  平台（E092），而上游把 udev 规则安装守卫写成
  `if (${CMAKE_SYSTEM_NAME} MATCHES "Linux" AND INDI_INSTALL_UDEV_RULES)` →
  走 Linux 路径才能让该安装生效（同族 `archives/l/libfli` 配方的既有做法）。
- **`INDI_ROOT`** = libindi 包的 package_folder（让仓内 `cmake_modules/FindINDI.cmake`
  命中预构建 libindi）。
- **`INDI_DATA_DIR="share/indi"`（相对）**：本驱动 CMakeLists 直接用 `${INDI_DATA_DIR}`
  安装 XML，而仓内 finder 会用 `find_path` 把它解析成 **libindi 包的绝对路径** → 不预置就会把
  `indi_lunatico.xml` 写进**依赖包**（复用 DRAFT-24001 的结论）。
- **`RULES_INSTALL_DIR="lib/udev/rules.d"`（相对）**：上游把该变量**硬编码**为绝对路径
  `/usr/lib/udev/rules.d/`，在宿主机上不可写（root 所有，会写穿包前缀/失败）。按同族
  `archives/l/libfli` 的既有做法重定向进本包私有前缀 —— 既不丢产物也不改上游源码。
- **libnova 头目录注入**：indi 头链 `indidome.h → libastro.h → <libnova/utility.h>`，
  上游只 `include_directories(${INDI_INCLUDE_DIR})` → 用 `tc.extra_cflags/extra_cxxflags`
  注入（R33）。**注意**：按同族 libfli 的写法，值内**不要再嵌引号**（Conan 会把值包进
  CMake 引号串，内层引号会提前终止该串而使标志失效）。

### 3. 构建（build()）
```bash
cmake.configure(build_script_folder="indi-armadillo-platypus")   # 只配置本驱动子目录
cmake.build()
```
外加 1 个构建脚本补丁（见下）。

### 4. 打包（package()）
`cmake.install()`；产物：
`bin/{indi_seletek_rotator, indi_dragonfly_dome, indi_dragonfly, indi_beaver_dome,
indi_armadillo_focus, indi_platypus_focus}` +
`share/indi/indi_lunatico.xml`（6 条 `<driver>`：Armadillo/Platypus focuser、DragonFly
Controller、Seletek Rotator、DragonFly Dome、Beaver Dome）+
`lib/udev/rules.d/99-armadilloplatypus.rules`（重定向落点）。

`package_info()`：`bindirs=["bin"]`、`resdirs=["share"]`、`libdirs=["lib"]`（承载 udev
规则目录），并把 libindi 的 lib 目录 `prepend_path` 到 `LD_LIBRARY_PATH`（libindi 静态优先
发布，驱动实际动态链接其 `.so`）。

## 构建脚本补丁

`patches/0001-indi-armadillo-platypus-CMakeLists-link-indi-client.patch`：把
`find_package(INDI REQUIRED)` 改为 `find_package(INDI COMPONENTS driver align client REQUIRED)`。

原因：`FindINDI.cmake` 在调用者不给 `COMPONENTS` 时回落默认组件 `driver + align`，
驱动的 `DT_NEEDED` 只记录 `libindidriver` / `libindiAlignmentDriver`；而这两个库从
`libindiclient` 引入的符号（典型 `tty_write_string`）在链接期由兄弟 `.so` 顺带解析、
不会记入 `DT_NEEDED`，musl loader 运行期解析它们时会报
`Error relocating … symbol not found`。仅改构建脚本，不改被编译源码
（与同快照兄弟驱动的同类补丁一致）。

## 实测结果（本地 conan create，2026-10-07）

```
indi-armadillo-platypus/1.0-20221226082641: Apply patch (portability): ①请求 INDI client 组件…②RULES_INSTALL_DIR 改为相对路径…
[100%] Built target indi_seletek_rotator / indi_dragonfly_dome / indi_dragonfly /
                    indi_beaver_dome / indi_armadillo_focus / indi_platypus_focus      ← 6 个驱动全部编译
-- Installing: <pkg>/bin/indi_seletek_rotator …（共 6 个）
-- Installing: <pkg>/share/indi/indi_lunatico.xml
-- Installing: <pkg>/lib/udev/rules.d/99-armadilloplatypus.rules                       ← 重定向生效
indi-armadillo-platypus/1.0-20221226082641: Package '9819fc38…' created
[ok]   bin/: 6 个驱动均为 AArch64 ELF
[ok]   share/indi/indi_lunatico.xml: 6 条 <driver> 与 bin/ 逐一对应
[ok]   DT_NEEDED 闭包完整：6 个驱动均记录 libindiclient.so.2, libindidriver.so.2, libindiAlignmentDriver.so.2
[ok]   udev 规则已随包安装（重定向进私有前缀）
[skip] host refused to start the OHOS binary: [Errno 1] Operation not permitted: …/bin/indi_seletek_rotator
checks=6 fails=0 skips=2
RESULT: PASS
```

- 上游通过率：**N/A（上游该驱动目录确无自带用例，清点证据见下节）**；配方侧另新增 5 个 gtest 用例（审核口径 N=5），本机因环境限制未取得通过数（**不宣称**）
- 消费者校验：**6 项中 4 项通过 + 2 项按设计 SKIP**（宿主不允许从用户数据目录（$HOME，构建/包目录所在处）执行 OHOS 二进制——实测把系统自带的 busybox 复制到该目录同样报 Permission denied，属环境限制，非打包缺陷）
- 包创建成功（`Package … created`）

### 配方侧新增的单元测试（本 PR 新增，非上游资产）

上游该驱动目录**本身没有任何测试**（`CMakeLists.txt` 无 `enable_testing()`/`add_test()`；锁定 commit `945fbe12` 与 master 分支均已核对）。按审核口径把"有测试"补实，照兄弟驱动 `indi-maxdomeii` 的既有约定在**配方侧**新增：

- `tests/test_arm_plat_focuser.cpp`：5 个 gtest 用例，全部针对**与硬件无关**的真实接口（`getDefaultName()`、构造设置的能力位、`FOCUS_TEMPERATURE` 定义、Port 开关、Wiring/HalfStep 选项）
- 补丁 `0002`：在驱动 `CMakeLists.txt` 末尾追加 `if (INDI_BUILD_UNITTESTS)` 分支（`enable_testing()` + `find_package(GTest)` + `add_executable(test-armadillo-platypus …)` + `add_test(run-tests …)`），只新增测试目标、不动任何现有目标与源码
- 配方：`test_requires("gtest/1.17.0")`、`INDI_BUILD_UNITTESTS=ON`、注入 `GTEST_INCLUDE_DIRS`/`GTEST_BOTH_LIBRARIES`，`build()` 内经 `ctest` 执行；运行环境用 `VirtualRunEnv` 生成的 **conanrun**（覆盖 libindi 的传递依赖 libcurl/libfftw3/libgsl/libusb-1.0）

**本机实测**：测试目标编译成功、已注册进 ctest、ctest 已在 `build()` 内执行；但**本机未跑成**——宿主不允许从用户数据目录（`$HOME`，构建/包目录所在处）执行二进制（把系统自带的 busybox 复制进该目录同样报 `Permission denied`）；改用 `conanrun` 补齐传递依赖后，本机仍报 `Error relocating …test-armadillo-platypus: <INDI 的 C++ 符号> symbol not found`（加载器未能从所加载的 libindi 共享库解析出这些符号）。CI/真机（构建与执行不在用户数据目录）可正常执行。

## 踩坑记录：toolchain 预置被上游普通 `SET()` 遮蔽

第一轮构建**编译全部通过**，但 `package()` 失败：

```
CMake Error at cmake_install.cmake:178 (file):
  file cannot create directory: /usr/lib/udev/rules.d.  Maybe need administrative privileges.
```

即 udev 规则仍被装到上游硬编码的**绝对路径** `/usr/lib/udev/rules.d`。原因：我在 `generate()`
里用 `tc.variables["RULES_INSTALL_DIR"] = "lib/udev/rules.d"` 预置，但上游 CMakeLists 写的是

```cmake
SET(RULES_INSTALL_DIR "/usr/lib/udev/rules.d/")     # 普通变量（非 CACHE）
```

——**普通 `SET()` 会在目录作用域内遮蔽 toolchain 预置的同名 cache 变量**，预置因此失效。
对照同族 `libfli`（同一 repo 家族、同样有 udev 规则）：

```cmake
set(UDEVRULES_INSTALL_DIR "/usr/lib/udev/rules.d" CACHE STRING "…")   # CACHE → 预置可生效
```

所以 libfli 能用 `tc.variables["UDEVRULES_INSTALL_DIR"]="lib/udev/rules.d"` 生效，而本驱动不行。
**处置**：加补丁把该行改成相对的 `${CMAKE_INSTALL_LIBDIR}/udev/rules.d`（`GNUInstallDirs` 已
include），并去掉失效的 toolchain 预置（避免误导后来者）。这属于"绝对路径安装变量写穿包前缀"的
一类问题，与 `INDI_DATA_DIR` 那条（finder 解析出的绝对路径）成因不同、处置也不同。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 测试框架声明 | **无**：`CMakeLists.txt` 只有 6 条 `add_executable` + `target_link_libraries` + 若干 `install`，**无 `enable_testing()` / `add_test()`**（grep 计数 = 0） |
| 仓库级测试 | indi-3rdparty 全仓无这些驱动的测试用例 |
| 结论 | **上游确无测试** → `build()` 不跑上游套件；`upstream_test_pass_rate` 记 **N/A**（如实披露，不虚构） |
| 消费者验证 | `test_package/check_all_drivers.py` 5 项（多驱动逐一 ELF/XML/DT_NEEDED/udev 落点 + best-effort 运行） |

## 本包的两个新变化点（相对同族单驱动包）

1. **多驱动**：6 个可执行文件共享同一 CMake 工程与同一链接配置 → 消费者校验对**每一个**
   bin 做 ELF 审计与 DT_NEEDED 闭包审计，并把 XML 里的 6 条 `<driver>` 与 bin/ 逐一对应
   （多一条/少一条都算失败）。
2. **绝对路径安装变量**：`RULES_INSTALL_DIR=/usr/lib/udev/rules.d/`（写穿包前缀）→
   重定向进私有前缀；同时因为上游的 Linux 守卫，需要 `CMAKE_SYSTEM_NAME=Linux` 才会触发
   该安装。两处都沿用同族 `archives/l/libfli` 的既有做法。

## 复用来源

本配方与同快照兄弟驱动 **`archives/i/indi-talon6/2.0-20221222160901`**、
**`archives/i/indi-maxdomeii/1.3-20221223105522`**、**`archives/i/indi-aok/2.0-20221222093242`**
同构（同一 pin commit/sha256、同一子目录构建法、同一 `INDI_ROOT` 提示与 `LD_LIBRARY_PATH`
注入、同一 client 组件补丁、同一 `INDI_DATA_DIR` 预置结论、同一 libnova 头目录注入）；
uv 规则重定向与 `CMAKE_SYSTEM_NAME=Linux` 两条沿用同族 **`archives/l/libfli`**。
