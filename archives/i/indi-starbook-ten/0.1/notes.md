# indi-starbook-ten 0.1 适配笔记

## 任务定位

indi-starbook-ten 是 Vixen StarBook Ten 望远镜 mount 控制器（固件 >= 5.10）
的 INDI 驱动（可执行程序，非库）。源码小（109KB tarball，3 个驱动源文件 +
内置 cpp-httplib 单头），依赖 libindi/libnova（全部已在制品仓），
无 GUI/媒体/内核依赖，真机编译秒级。

与 indi-rtklib 同属 indilib/indi-3rdparty 家族，适配模式完全同款。

## 关键认知（实测）

1. **mount 走 HTTP 协议**：`StarbookTen` 协议客户端（`starbook_ten.cpp/h`）
   通过内置 `httplib.h`（cpp-httplib 单头）向 mount 发 GET 命令，
   响应为 `<!--KEY=VAL-->` HTML 注释格式，`std::regex` 解析。
2. **构建系统是 CMake**（`cmake_minimum_required(VERSION 3.0)`，
   `find_package(INDI/NOVA REQUIRED)`，`add_executable(indi_starbook_ten)`）。
3. **libindi 无 INDIConfig.cmake**：发布版 `package_info` 用
   `cmake_file_name=libindi`，与驱动 `find_package(INDI)` 不匹配，
   必须用驱动自带 `FindINDI.cmake`/`FindNova.cmake`（`cmake_modules/`），
   并由配方注入 `INDI_INCLUDE_DIR`/`INDI_LIBRARIES`/`NOVA_*`（同 rtklib）。
4. **libnova 仅两个符号**：协议客户端只调 `ln_deg_to_dms`/`ln_dms_to_deg`
   （setLatLonTz/getLatLon 路径），test_package 链 `-lnova -lm` 即可。

## 鸿蒙适配点

- **E092**：CMake 不识别 HarmonyOS → 强制 `CMAKE_SYSTEM_NAME=Linux`
  （同 libindi/rtklib 配方）。
- **CMake 4.x**：上游 `VERSION 3.0` → 注入 cache 变量
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`（必须 cache 变量，工具链文件变量
  加载太晚；仓内惯例，参照 fast_obj）。
- **libc++**：C++ 驱动目标链接 `c++`/`c++abi`（package_info system_libs）。
- **依赖注入**：FindINDI/FindNova 模块变量指向 conan 依赖包目录
  （`INDI_INCLUDE_DIR` 必须指到 `include/libindi` 子目录，见下节）。

## 真机第 1 轮失败复盘（G2 configure，2026-10-05 回报）

第 1 轮 G1/G0 通过，G2 configure 挂在
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
   `failed to detect INDI version`——2021 快照 FindINDI.cmake 的正则
   `.*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)` 匹配不了 INDI 2.x 的
   `#define INDI_VERSION "2.2.2"`（带引号）。**修复 = patch 0001**：
   逐字回移上游 master 修复行（与已合并 libfli/2.0 的 0001 补丁相同）。
3. **连锁雷 2**：`cmake_modules/CMakeCommon.cmake` 写死
   `set(CMAKE_CXX_STANDARD 14)`（目录级普通变量，遮蔽 conan toolchain 的
   cppstd=17），而 libindi 2.x 头文件用 `std::any`。**修复 = patch 0002**：
   14→17。
4. **连锁雷 3**：2021 驱动源码用 libindi 1.x API（`SlewRateS`、
   `LocationN`/`TimeT`、`operator&` 取 property 指针、
   `initGuiderProperties`/`processGuiderProperties` 等），在 libindi
   2.2.2 下 20+ 处编译错误。**修复 = patch 0003**：整文件回移上游
   indi-3rdparty master 的 `indi_starbook_ten.cpp`（其头文件
   `indi_starbook_ten.h` 与 0.1 快照逐字一致），外加 `starbook_ten.cpp`
   的 `fabs()` 负坐标修复。**已在 WSL 用制品仓真 OHOS 头文件+真包验证：
   打补丁后 3 个翻译单元全部编译通过**（链接因 x86_64 主机遇 aarch64
   .so 失败，属预期，真机无此问题）。
5. **NOVA_INCLUDE_DIR 保持包根 `include/` 不动**：驱动源码写的是带前缀的
   `<libnova/julian_day.h>`；FindNova 对注入变量直接短路采信，不校验。

## test_package（R34 真实 API 测试）

驱动要连真实 mount 才能完整运行，无法直接当库链接。采用两层：

- **Layer 1（真实 API，localhost mock）**：package() 把
  `starbook_ten.cpp/.h` + `httplib.h` vendor 进 `<pkg>/src`；test_package
  编译 `test.cpp` + `starbook_ten.cpp`，用 httplib 同头文件自带的
  `httplib::Server` 在 127.0.0.1 起 mock mount（`bind_to_any_port`，
  不占固定端口），应答罐装 StarBook 响应，然后真实调用四组公开 API：
  - `getFirmwareVersion()` → 解析 `<!--VERSION=5.10-->` → (5,10)
  - `getStatus()` → 解析 `<!--RA=5.5000&DEC=-20.2500&GOTO=0&STATE=SCOPE-->`
    → ra/dec/goto_busy/STATE_SCOPE
  - `getPierSide()` → `PIERSIDE=1` → PIERSIDE_EAST 枚举映射
  - `stop()` → 命令端点 `<!--OK-->` 确认
- **Layer 2（二进制烟测）**：检查 `bin/indi_starbook_ten` 存在并运行 `--help`。

## 验证（Windows 本机，非 OHOS 真机）

- 源码 sha256 实测匹配：`f8f5ca69...`（Debian pool 0.1.orig.tar.gz）。
- Layer 1 在 WSL x86_64 gcc 下**编译通过、6 项断言全过**
  （`firmware: 5.10` / `status: ra=5.5000 dec=-20.2500 goto=0 state=3` / PASS）。
  ⚠️ 如实声明：本机无 x86_64 libnova（sudo 不可用装不了），链接用了
  `ln_deg_to_dms`/`ln_dms_to_deg` 两符号的 stub——这两个符号在被测路径
  上不会被调用（仅 setLatLonTz/getLatLon 用），stub 只为过链接；
  头文件用的是制品仓 OHOS libnova 包的真头文件（架构无关）。
  真机上由 conan 依赖图提供真 libnova，不存在此缺口。
- conanfile/test_package 语法 `py_compile` 通过，`conan export` 通过。

> ⚠️ 上述均为 Windows/WSL 本机结果，**不等于 OHOS 真机通过**。真机构建/测试
> 待 MateBook 按仓库 SKILL 执行（见文末验证项）。

## 已知限制

- 上游无测试套件（MANIFEST 已声明 `upstream_test_in_build: false`）。
- 驱动完整功能需连接 StarBook Ten mount，真机仅做编译 + 协议客户端
  mock API 测试 + 二进制烟测。

## MateBook 真机验证项（OHOS）

> 前置：Fork `gcw_caeRdY6E/build_in_harmonyos` 保持**公开**
> （MateBook 不存 git 凭据，只拉公开分支）。

```bash
# 1. 拉分支（在 MateBook 已有克隆里）
git remote add fork https://atomgit.com/gcw_caeRdY6E/build_in_harmonyos.git  # 加过则跳过
git fetch fork
git checkout -b verify/starbook-ten fork/feat/indi-starbook-ten-0.1

# 2. conan remote 预检（ohpcd 易丢，先查后补）
conan remote list
# 缺失则: conan remote add --force ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/

# 3. R36 依赖预检（两依赖须已在制品仓）
conan download --only-recipe libindi/2.2.2.1 -r=ohpcd
conan download --only-recipe libnova/0.16 -r=ohpcd

# 4. 标准验证（W2 结构 → R36 依赖 → G2 conan create 干净构建 → test_package）
python3 scripts/ohc-run.py conan-verify indi-starbook-ten 0.1

# 5. 通过后收尾（自动写 .ci-result.json，含日志哈希，禁手改）
python3 scripts/ohc-run.py finish indi-starbook-ten 0.1 built
```

### 风险清单（真机踩坑预案）

| 风险点 | 现象 | 排查方向 |
|---|---|---|
| R36 依赖闸 | 前置依赖检查失败 | 两依赖须已在制品仓：libindi/2.2.2.1、libnova/0.16 |
| FindINDI 头路径 | `INDI version header not found`（FindINDI.cmake:212） | libindi 包全部头文件在 `include/libindi/`；`INDI_INCLUDE_DIR` 必须指到该子目录（第 1 轮已踩，已修）；若复发查分支是否同步 |
| FindINDI 版本正则 | `failed to detect INDI version` | 2021 快照正则不吃 INDI 2.x 引号版本宏；patch 0001 已修（同 libfli 先例）；若复发查补丁是否应用 |
| C++ 标准 | `std::any`/`std::variant` 相关报错 | CMakeCommon.cmake 锁死 gnu++14 遮蔽 toolchain cppstd=17；patch 0002 已修 |
| libindi 1.x API | `LocationN`/`SlewRateS`/`operator&`/`initGuiderProperties` 未声明 | patch 0003 已整文件回移上游 master 迁移；若复发查补丁是否应用 |
| E092 | cmake 不识别 HarmonyOS system | 配方已强制 `CMAKE_SYSTEM_NAME=Linux`；若仍报错查 toolchain 是否生效 |
| CMake 4.x | configure 报 `Compatibility with CMake < 3.5 has been removed` | 配方已注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量）；查分支是否同步到最新提交 |
| libc++ 链接 | 链接期缺 `c++`/`c++abi` 符号 | package_info system_libs 已声明；查 OHOS SDK libc++ 路径 |
| Layer1 mock 服务器 | mock bind 失败 / `is_running` 一直 false | 已用 `bind_to_any_port` 避开固定端口冲突；查 127.0.0.1 回环是否可用；test 有 try/catch，异常会打印 |
| Layer1 链接 | 缺 `ln_deg_to_dms`/`ln_dms_to_deg` 符号 | test_package 已 `requires("libnova/0.16")` 并链 `-lnova -lm`；查 libnova 包 lib 目录 |
| Layer2 烟测 | `indi_starbook_ten --help` 缺失/失败 | 查 package() 是否装进 bin/；驱动完整功能需真实 mount 属正常，烟测只看 --help |
| 构建超时 | 默认预算 3600s | 源码 109KB 秒级构建；变慢说明依赖被 `--build=missing` 拉去源码编译 → 先查 R36 |

预期结果：conan-verify 全绿 → `finish ... built` → `reports/` 与 `.ci-result.json`
留本地作 PR 证据（**不提交**，参照已合并配方如 libindi/2.2.2.1 的目录构成）。
---

### 第 4 轮真机打包/签名实验与 step5b 根因备录（2026-10-06）

- `verify-build` PASS；PackageBuilder 10 步全过（rpath→strip→签名→tar.gz）。notes.md 编译结束回写与 `packaging/.packaged` 已随 `dc8f9eb37`、`36a3d3da7` 提交。
- **签名实验（EPERM 假设了结）**：签名后二进制 exec 已由 loader 正常启动——此前各轮 `--help` 的 EPERM/126 系未签名所致（同 E489 记载），非环境硬限制。本轮实测 rc=127 为 `libindidriver.so.2`/`libindiAlignmentDriver.so.2` 缺失：PackageBuilder step4「收集外部依赖」搜索路径不含 conan 依赖包目录，libindi 的 .so 闭包未收进包（lib/external 为空）。`.staging-verified` 按诚实口径未创建。
- **第 5 轮处置**：staging prefix（包内容 + libindi .so 闭包置入 lib/external/）重打包 → exec 实验 rc=0 后补 `.staging-verified` → finish 复跑。
- **step5b（W5 知识图谱完整性）FAIL 根因**：`workflow_checks.py` 必填字段检查不解析 YAML 块标量，把 main 仓既有 `E219/E253/E305` 的 `root_cause: |`（及 E305 `rec_approach: |`）误判为空——WSL 干净检出同结果复现，属全局性检查器缺陷，与本包配方无关；修复需改 `knowledge/` 框架文件，W2 原子性禁止混入本 PR。manifest 知识行 unreferenced=5 为粗检口径（step5b 设计上容忍 rc2=3，与已合并 libindi 同口径），不另处理。
- 运行手册补录：`conan cache path <pkg>/<ver>` 返回 exports 目录；取真实包目录须 `conan cache path <pkg>/<ver>:<package-id>`。
---

**编译结束**: 2026-10-07 12:15
**最终状态**: built
