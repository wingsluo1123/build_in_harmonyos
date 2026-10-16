# indi-rtklib 1.0-20221222172722 适配笔记

## 任务定位

indi-rtklib 是 INDI 天文框架的 RTKLIB 精密定位**驱动**（可执行程序，非库）。
源码极小（43KB，3 个源文件），依赖 libindi/libnova/zlib（全部已在制品仓），
无 GUI/媒体/内核依赖，真机编译秒级。

## 关键认知（实测）

1. **不是纯 RTKLIB 库**：上游包只含 INDI 驱动包装（`rtklib_driver.cpp`
   继承 `INDI::GPS` + 独立 C 解析器 `rtkrcv_parser.c`），不打包 RTKLIB 算法源码。
2. **构建系统是 CMake**（非 makefile），`find_package(INDI/NOVA REQUIRED)`。
3. **libindi 无 INDIConfig.cmake**：发布版 `package_info` 用 `cmake_file_name=libindi`，
   与驱动的 `find_package(INDI)` 不匹配，必须用驱动自带的 `FindINDI.cmake`，
   并由配方注入 `INDI_INCLUDE_DIR`/`INDI_LIBRARIES`/`NOVA_*`。

## 鸿蒙适配点

- **E092**：CMake 不识别 HarmonyOS → 强制 `CMAKE_SYSTEM_NAME=Linux`（同 libindi 配方）。
- **libc++**：C++ 驱动目标链接 `c++`/`c++abi`（package_info system_libs）。
- **依赖注入**：FindINDI/FindNova 模块变量指向 conan 依赖包目录
  （`INDI_INCLUDE_DIR` 必须指到 `include/libindi` 子目录，见下节）。

## 真机第 3 轮失败复盘（G2 configure，2026-10-05 回报）

第 1/2 轮已分别修掉 G1 样板与 CMake 4.x 策略；第 3 轮 G1/G0 通过、
`CMAKE_POLICY_VERSION_MINIMUM=3.5` 生效，G2 configure 挂在
`FindINDI.cmake:212: INDI version header not found`。根因链与修复：

1. **INDI_INCLUDE_DIR 指错层**：配方注入的是包根 `include/`，但发布的
   libindi/2.2.2.1 包**全部 87 个头文件都在 `include/libindi/` 下**
   （已 `conan download` 制品仓真包核实）。注入的 cache 变量使
   `find_path` 短路、不再追加 `PATH_SUFFIXES libindi`，于是
   `EXISTS ${INDI_INCLUDE_DIR}/indiversion.h` 落空 → FATAL。
   **修复**：注入 `include/libindi`；同时改注入 `INDI_ROOT=<包根>` 替代
   无效的 `INDI_LIBRARIES`（FindINDI 对默认 driver+align 组件做
   `find_library(HINTS ${INDI_ROOT} PATH_SUFFIXES lib64 lib)`，注入的
   INDI_LIBRARIES 会被模块覆盖；包内 `libindidriver` 与
   `libindiAlignmentDriver` 均在，align 无静态档只 .so，按默认解析链接）。
2. **连锁雷 1（同门 libfli 已趟过）**：头文件找到后下一步必炸
   `failed to detect INDI version`——2022 快照 FindINDI.cmake 的正则
   `.*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)` 匹配不了 INDI 2.x 的
   `#define INDI_VERSION "2.2.2"`（带引号）。**修复 = patch 0001**：
   逐字回移上游 master 修复行（与已合并 libfli/2.0 的 0001 补丁相同）。
3. **连锁雷 2**：`cmake_modules/CMakeCommon.cmake` 写死
   `set(CMAKE_CXX_STANDARD 14)`（目录级普通变量，遮蔽 conan toolchain 的
   cppstd=17），而 libindi 2.x 头文件用 `std::any`。**修复 = patch 0002**：
   14→17。
4. **连锁雷 3**：2022 驱动源码用 libindi 1.x GPS API（`LocationN`/`TimeT`/
   `IUSaveText(&TimeT[..])`），在 libindi 2.2.2 下编译错误；且驱动自带的
   `setSystemTime()` 走 `stime()` 回退分支（OHOS libc 无 stime）。
   **修复 = patch 0003**：回移上游 indi-3rdparty master 的
   `rtklib_driver.{cpp,h}`——`LocationNP`/`TimeTP` 迁移 + 删除自定义
   `setSystemTime()`（libindi 2.2.2.1 基类实现已由 libindi 配方修为
   `clock_settime`）。**已在 WSL 用制品仓真 OHOS 头文件+真包验证：
   打补丁后两个翻译单元全部编译通过**（链接因 x86_64 主机遇 aarch64
   .so 失败，属预期，真机无此问题）。
5. **NOVA_INCLUDE_DIR 保持包根 `include/` 不动**：驱动源码写的是带前缀的
   `<libnova/julian_day.h>`；FindNova 对注入变量直接短路采信，不校验。
6. **新增 ZLIB_ROOT 注入**：`find_package(ZLIB)` 在 INDI 之后，真机尚未
   走到；builtin FindZLIB 吃 `ZLIB_ROOT`（toolchain 的 CMAKE_PREFIX_PATH
   也覆盖包目录）， zlib 包为标准 `include/zlib.h` + `lib/libz.a` 布局，
   一并消除未知数。

## test_package（R34 真实 API 测试）

驱动要连 GPS 设备才能完整运行，无法直接当库链接。采用两层：

- **Layer 1（真实 API）**：package() 把 `rtkrcv_parser.c/.h` vendor 进 `<pkg>/src`，
  test_package 编译 `test.c` + `rtkrcv_parser.c`，真实调用公开 C API
  `scansolution()`。断言两个**实测可识别**的 fix 状态：
  - `(------)` → `status_no_fix`
  - `(SINGLE)` → `status_single`
- **Layer 2（二进制烟测）**：检查 `bin/indi_rtklib` 存在并运行 `--help`。

### 上游解析器的真实行为（实测，如实记录）

`scansolution()` 用 `sscanf(solution,"(%6c)",status)` 读取状态，**不带 `)` 终止符**：
- 恰好 6 字符的状态（`SINGLE`、`------`）能正确匹配；
- 短状态名（`FIX`/`FLOAT`/`SBAS`/`DGPS`/`PPP`）会被读成 `FIX)`/`FLOAT)` 等，
  **无法识别**（上游 quirk，非本移植引入）。

因此 test_package **只断言上游真正能识别的两个状态**，不为短状态名写预期。

## 验证（Windows 本机，非 OHOS 真机）

- 源码 sha256 实测匹配：`49028a1c...`
- `rtkrcv_parser.c` + 测试用例在 WSL gcc 13.3 下编译通过，`no_fix`/`SINGLE`
  两状态识别实测正确。
- conanfile/test_package 语法 `py_compile` 通过。

> ⚠️ 上述均为 Windows/WSL 本机结果，**不等于 OHOS 真机通过**。真机构建/测试
> 待 MateBook 按仓库 SKILL 执行（见文末验证项）。

## 已知限制

- 上游无测试套件（MANIFEST 已声明 `upstream_test_in_build: false`）。
- 驱动完整功能需连接 GPS 设备，真机仅做编译 + 解析器 API + 二进制烟测。

## MateBook 真机验证项（OHOS）

> 前置：Fork `gcw_caeRdY6E/build_in_harmonyos` 保持**公开**
> （MateBook 不存 git 凭据，只拉公开分支）。

```bash
# 1. 拉分支（在 MateBook 已有克隆里）
git remote add fork https://atomgit.com/gcw_caeRdY6E/build_in_harmonyos.git  # 加过则跳过
git fetch fork
git checkout -b verify/indi-rtklib fork/feat/indi-rtklib-1.0-20221222172722

# 2. conan remote 预检（ohpcd 易丢，先查后补）
conan remote list
# 缺失则: conan remote add --force ohpcd <制品仓URL>

# 3. R36 依赖预检（SKILL W2 口径：conan download --only-recipe 验证已发布）
conan download --only-recipe libindi/2.2.2.1 -r=ohpcd
conan download --only-recipe libnova/0.16 -r=ohpcd
conan download --only-recipe zlib/1.3.1.1 -r=ohpcd

# 4. 标准验证（W2 结构 → R36 依赖 → G2 conan create 干净构建 → test_package）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify indi-rtklib 1.0-20221222172722

# 5. 通过后收尾（自动写 .ci-result.json，含日志哈希，禁手改）
python3 $SKILL_ROOT/scripts/ohc-run.py finish indi-rtklib 1.0-20221222172722 built
```

### 风险清单（真机踩坑预案）

| 风险点 | 现象 | 排查方向 |
|---|---|---|
| R36 依赖闸 | 前置依赖检查失败 | 三依赖须已在制品仓；zlib 必须 1.3.1.1（对齐 libindi），解析成其他版本即冲突 |
| FindINDI 头路径 | `INDI version header not found`（FindINDI.cmake:212） | libindi 包全部头文件在 `include/libindi/`；`INDI_INCLUDE_DIR` 必须指到该子目录（第 3 轮已踩，已修）；若复发查分支是否同步 |
| FindINDI 版本正则 | `failed to detect INDI version` | 2022 快照正则不吃 INDI 2.x 引号版本宏；patch 0001 已修（同 libfli 先例）；若复发查补丁是否应用 |
| C++ 标准 | `std::any`/`std::variant` 相关报错 | CMakeCommon.cmake 锁死 gnu++14 遮蔽 toolchain cppstd=17；patch 0002 已修 |
| libindi 1.x API | `LocationN`/`TimeT`/`stime` 未声明 | patch 0003 已回移上游 master 迁移并删除驱动自带 setSystemTime；若复发查补丁是否应用 |
| E092 | cmake 不识别 HarmonyOS system | 配方已强制 `CMAKE_SYSTEM_NAME=Linux`；若仍报错查 toolchain 是否生效 |
| libc++ 链接 | 链接期缺 `c++`/`c++abi` 符号 | package_info system_libs 已声明；查 OHOS SDK libc++ 路径 |
| test_package 断言 | `FIX`/`FLOAT` 状态识别失败 | **上游 UB 已由 patch 0004 修复**——现断言 no_fix/SINGLE/FIX/FLOAT 四态全部确定性识别；若失败查 0004 是否应用、分支是否同步 |
| Layer2 烟测 | `indi_rtklib --help` 缺失/失败 | 查 package() 是否装进 bin/；驱动完整功能需 GPS 设备属正常，烟测只看 --help |
| 构建超时 | 默认预算 3600s | 源码 43KB 秒级构建，正常无需 `timeout set`；变慢说明依赖被 `--build=missing` 拉去源码编译 → 先查 R36 |

预期结果：conan-verify 全绿 → `finish ... built` → `reports/` 与 `.ci-result.json`
留本地作 PR 证据（**不提交**，参照已合并配方如 libindi/2.2.2.1 的目录构成）。
---

### 第 6 轮真机打包/签名实验与 step5b 根因备录（2026-10-06）

- `verify-build` PASS（G2 干净重建，无 EPERM FAIL）；PackageBuilder 10 步全过：0 符号链接、rpath→strip→签名→主 tar.gz 101414B + debug 51228B。`packaging/.packaged`（25+ 已合并先例同口径 force-add）与 `.build-closed`（cloog 先例）已随 `c4cda4e7f` 提交。
- **签名实验（EPERM 假设了结）**：签名后二进制 exec 已由 loader 正常启动——此前各轮 `--help` 的 EPERM/126 系未签名所致（同 E489 记载），非环境硬限制。本轮实测 rc=127 为 `libindidriver.so.2`/`libindiAlignmentDriver.so.2` 缺失：PackageBuilder step4「收集外部依赖」搜索路径（`src_prefix/lib`、`~/usr/local/lib`、`/data/service/hnp/lib`、`/usr/lib*`）不含 conan 依赖包目录，libindi 的 .so 闭包未收进包（lib/external 为空）。`.staging-verified` 按诚实口径未创建。
- **第 7 轮处置**：staging prefix（包内容 + libindi .so 闭包置入 lib/external/）重打包 → exec 实验 rc=0 后补 `.staging-verified` → finish 复跑。
- **step5b（W5 知识图谱完整性）FAIL 根因**：`workflow_checks.py` 必填字段检查不解析 YAML 块标量，把 main 仓既有 `E219/E253/E305` 的 `root_cause: |`（及 E305 `rec_approach: |`）误判为空——WSL 干净检出同结果复现，属全局性检查器缺陷，与本包配方无关；修复需改 `knowledge/` 框架文件，W2 原子性禁止混入本 PR。manifest 知识行 unreferenced=5 为粗检口径（step5b 设计上容忍 rc2=3，与已合并 libindi 同口径），不另处理。
- 运行手册补录：`conan cache path <pkg>/<ver>` 返回 exports 目录；取真实包目录须 `conan cache path <pkg>/<ver>:<package-id>`。
---

**编译结束**: 2026-10-07 12:19
**最终状态**: built
