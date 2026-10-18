# kcolorscheme 6.28.0 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/frameworks/kcolorscheme>
版本: 6.28.0（KDE Frameworks 6.28 发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

构建产物：`lib/libKF6ColorScheme.so`（单一无版本实体文件）。库本体为
KDE Frameworks 6 色彩方案库：KColorScheme 语义颜色角色查询（背景 /
前景 / 装饰 × 7 类 ColorSet × Active/Inactive 态）、KColorSchemeManager
方案管理、KColorSchemeModel 方案模型、KStatefulBrush 状态感知画刷、
KColorUtils 对比度工具；BreezeLight/BreezeDark 配色经 qt_add_resources
以 rcc 编入库内（无独立 data 文件）。

适配要点：2 个补丁（`0001` 降 KF_DEP_VERSION、`0002` 可重定位基名
SONAME 链接），全部经 conandata.yml 声明并由 `apply_conandata_patches`
应用；`BUILD_TESTING=ON`，上游唯一 autotest 目标 kcolorschemetest
（3 个 QTest 函数、10 个数据行用例）全部进入真机 ctest；
conandata.yml 另携带 R39 五源回退列表（官方源 + bfsu/ustc/nju/aliyun）。

## 二、问题与处置

### 问题 1：download.kde.org 源下载 TLS 证书校验失败（R39）

源码归档域名 download.kde.org（Mirrorbits）在 CN 网络 302 跳转到
regional 镜像 mirrors.bfsu.edu.cn，该镜像 TLS 证书在校园 PC 与真机
网络均校验失败（self-signed）；mirrors.ustc.edu.cn 亦 302 到
mirrors4.bfsu.edu.cn 同败（真机 source() 首枪实录
`SSL: CERTIFICATE_VERIFY_FAILED ... self-signed certificate`，3 次重试
后 RC=1）。**处置**（kbookmarks / kauth 6.28.0 先例）：conandata.yml
给出「官方源 + bfsu/ustc/nju/aliyun」URL 列表，conan get() 按序回退
（每项 3 次重试后转下一项）；四个镜像在 PC 侧逐一实下并与官方 tarball
比对 sha256 / 逐字节一致（51804 bytes）。真机实测由第 4 项
mirror.nju.edu.cn 命中（日志实录 `Sources correctly downloaded from
https://mirror.nju.edu.cn/...`）。

### 问题 2：ohpcd 的 KF6 依赖栈止步 6.26.0（补丁 0001）

上游要求 KF6 >= 6.28.0（`KF_DEP_VERSION 6.28.0`）。ohpcd 制品仓的 KF6
stack 止步 6.26.0：kconfig 有 .1 修复版（6.26.0.1），kguiaddons / ki18n
停在 6.26.0（无 .1）。**处置**：只降 `KF_DEP_VERSION` 一行到 6.26.0；
`find_package(ECM 6.28.0)` 线不动——extra-cmake-modules/6.29.0
（tool 包）满足它。

### 问题 3：KF6 库无 DT_SONAME，绝对路径链接把机器私有路径烧进 DT_NEEDED（补丁 0002）

发布的 KF6 库不带 DT_SONAME（其导出 targets 带
`IMPORTED_NO_SONAME=TRUE`），按绝对 Conan 缓存路径链接会把机器私有
路径烧进 libKF6ColorScheme.so 的 DT_NEEDED（非可重定位，E537）。
**处置**（krunner 6.28.0 / kscreenlocker 6.7.2 `0008` / kpackage
6.26.0.1 `0005` 先例，真机实证）：

- lld 按命令行原样记录库名，因此源码实际消费的四个 KF6 组件
  （ConfigCore / ConfigGui / GuiAddons / I18n）改按 `-l:libKF6Xxx.so`
  精确文件名链接（裸基名），依赖目录以
  `target_link_directories(... PRIVATE)` 挂给 KF6ColorScheme；
- `KF6::ConfigCore` 留 INTERFACE 按名导出（公共头 include
  `<KSharedConfig>`；包内 KF6ColorSchemeConfig.cmake 上游自带
  `find_dependency(KF6Config)`，绝不绝对路径）；
- `Qt6::Gui` 保持导入目标（Qt6 库有真 versioned SONAME）；Qt6GuiPrivate
  同保持导入目标；
- 离开链接行的依赖其使用需求（include 目录 / 定义）按
  `INTERFACE_LINK_LIBRARIES` 传递闭包拷贝，每个 `get_target_property`
  带 `-NOTFOUND` 哨兵门（KDE targets 文件只设 per-config 的
  `IMPORTED_LOCATION_RELEASE`，非空哨兵串会被朴素 `if(NOT var)`
  误判为"已设置"）；
- 平台模块无 soname flag 时直传 `-Wl,-soname,libKF6ColorScheme.so`
  （Linux 有平台 flag 时跳过，保住上游版本化行为）。

配方侧相关事实：不设 `CMAKE_SHARED_LIBRARY_SONAME` flags、上游
VERSION/SOVERSION 不落版本链——产物天然为单一无版本实体 .so（OHOS
/storage 禁 symlink，版本化符号链创建必 EPERM；kpackage/6.26.0.1 /
kcolorscheme 6.26.0 先例）。

## 三、依赖解析

| 上游需求 | ohpcd 选择 | 说明 |
| --- | --- | --- |
| Qt6 >= 6.9.0（Core/Gui，GuiPrivate for Qt >= 6.10，Test for autotests） | qtbase/6.11.1 | Qt6GuiPrivate 属 qtbase 包（Qt >= 6.10） |
| KF6 >= 6.28.0（Config/GuiAddons/I18n 均 REQUIRED） | kconfig/6.26.0.1、kguiaddons/6.26.0、ki18n/6.26.0 | 补丁 0001 降版；kconfig .1 注入裸 DT_SONAME，kguiaddons / ki18n 无 .1（无 DT_SONAME——补丁 0002 的 `-l:` 链接对两种形态都可重定位） |
| ECM >= 6.28.0 | extra-cmake-modules/6.29.0（tool_require） | find 线保留；CMakeDeps 生成的 ECMConfig 不带 ECM_MODULE_PATH，配方手工注入三个子目录 |

## 四、真机验证

- 首枪（2026-10-17）：source() 在 download.kde.org→bfsu 镜像 TLS 校验
  处失败（问题 1 实录）→ conandata.yml 改五源回退列表。
- 第二枪（交付构建）：全链 `conan create` —— 源码由 mirror.nju.edu.cn
  命中下载 → 全量编译 100%（仅上游一处 deprecated-enum 警告，无害）→
  上游 ctest `1/1 Test #1: kcolorschemetest ... Passed 0.63 sec`
  （`100% tests passed, 0 tests failed out of 1`）→ 打包 + 重签
  （`Signed 1 OHOS package ELF file(s)`；Package
  `cd8a4450532fb9da93e39dc0c3fd0ce1ac341bc4` built）→ test_package：
  fixdeps 扫描走完、无需补位 → ELF 制品检查 20/20（8 条基名 DT_NEEDED、
  DT_SONAME=libKF6ColorScheme.so、`.codesign` 在场）→ 消费者 29/29
  （`TEST SUMMARY: 29 passed, 0 failed`）→ **RC=0**。
- 收官（2026-10-17，conan-verify）：首次运行 G1 判缺
  `test_package/MANIFEST.yml`（CI L0e 门禁）→ 补 MANIFEST.yml（本文件
  同目录）后重跑。因 MANIFEST.yml / manifest.yaml / notes.md / reports
  均不入 recipe revision，首跑秒级完成实为缓存复用（"Already
  installed!"）；`conan remove "kcolorscheme/6.28.0*" -c` 清本地缓存后
  干净重建全链：source（5-URL 列表，源码缓存种子命中，日志实录
  `Source [...] retrieved from local download cache`）→ 补丁 0001/0002
  应用 → configure `-- Configuring done (12.2s)` → 100% 编译（含
  kcolorschemetest）→ 上游 ctest `Passed 0.72 sec`
  （`100% tests passed, 0 tests failed out of 1`，Total 0.75）→ 打包重签
  （`Signed 1 OHOS package ELF file(s)`；`Package
  'cd8a4450532fb9da93e39dc0c3fd0ce1ac341bc4' built`，与交付构建同 id）→
  test_package：fixdeps `scanned 150 runtime libraries` +
  `no path-carrying DT_NEEDED entries found` → `OK: 20 OHOS artefact
  checks passed` → 消费者直跑 `TEST SUMMARY: 29 passed, 0 failed` → ctest
  `test_kcolorscheme Passed 0.12 sec` → **Verdict PASS（G0–G4 全 ✅；
  L2/L4/L5 跳过=无 cache 路径）RC=0**；报告随档
  `reports/conan-verify-report.md`。
- 交付版文件与设备档案（`$HOME/bih/archives/k/kcolorscheme/6.28.0`）
  md5 逐件一致（清单见 MR 正文）。

## 五、交付物

- `lib/libKF6ColorScheme.so`——单一无版本实体共享对象（OHOS /storage
  禁 symlink，无版本链），DT_SONAME=libKF6ColorScheme.so、DT_NEEDED 全
  基名、安装文件已重签（`.codesign` 在场）
- `patches/0001` / `0002` + conandata.yml 声明（每补丁带说明与
  portability 分类；含 R39 五源回退列表）
- test_package：消费者 E2E 29 用例（行为）+ 制品检查 20 项（12+N，
  N=8，ELF 结构）+ fixdeps 注册表卫生扫描
- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档
  脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
