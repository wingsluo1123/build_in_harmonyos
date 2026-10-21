# killbots 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake (Qt6/KF6/ECM)
- 编译日期: 2026-10-15
- 编译器: clang 15 / clang++ (OHOS SDK)
- 状态: published

## 编译步骤

```bash
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON \
  -DBUILD_TESTING=OFF \
  -DKF_IGNORE_PLATFORM_CHECK=TRUE \
  -DKF_SKIP_PO_PROCESSING=ON \
  -DECM_MODULE_PATH=/path/to/ecm/share/ECM/modules\;...
make -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | DocTools 未发布到 KF6 closure | KF6 6.18 不含 kdoctools | build() 内替换 CMakeLists.txt 跳过 DocTools + doc/ 子目录 |
| 2 | KDE 平台检测失败 | OHOS 不在 KDE 平台列表 | KF_IGNORE_PLATFORM_CHECK=TRUE |
| 3 | musl 加载器 max-page-size 冲突 | OHOS musl 默认 64KB | -Wl,-z,max-page-size=0x1000 |
| 4 | cmake_find_mode=none 时 find_package 找不到依赖 | 手动设置 ECM_MODULE_PATH | _write_cmake_paths 注入 prefix path |

## 源码修改

- `conanfile.py` build(): 直接替换 CMakeLists.txt，移除 KF6 DocTools、doc/ 子目录与 kdoctools_install(po)（klickety precedent）

## 依赖版本

- qtbase/6.11.1, qtsvg/6.11.1
- karchive/6.18.0 (override), kconfig/6.18.0, kconfigwidgets/6.18.0, kcoreaddons/6.18.0, kcrash/6.18.0, kdbusaddons/6.18.0, ki18n/6.18.0, kiconthemes/6.18.0.1, kwidgetsaddons/6.18.0, kxmlgui/6.18.0
- libkdegames/26.04.0
- ecm/6.26.0 (tool_requires)

## 验证结果

```bash
# conan create 本地构建验证
conan create . --build=missing  # RC=0, 产物 bin/killbots

# test_package smoke test
./killbots --version  # → 26.04.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/killbots | ~500KB | KDE 游戏可执行文件 |

## 注意事项

- 上游 enginetest 需要完整 KDE CI 基础设施，BUILD_TESTING=OFF 跳过
- test_package 包含鸿蒙特有消费者测试：dlopen libQt6Core 闭包 + .codesign 签名

### 对话 #1（2026-10-15 会话：适配与构建）

- 用户指令：killbots/26.04.0 适配 HarmonyOS PC，前置条件所有依赖 conan download 可消费（R36），完整流程 conan create → test_package → conan-verify → finish → W2/W3 → PR 原子性；上游测试实际执行并单独汇报；至少新增一个鸿蒙特有非断言测试。
- 依赖图解析：33 包全部消费 ohpcd 制品仓。关键点 kiconthemes/6.18.0（kxmlgui 依赖）与其新版本 6.18.0.1 并存：6.18.0 的依赖组合（karchive/6.19.0 + ecm/6.19.0）与主图冲突触发本地重建，其 ctest kpixmapsequenceloadertest 需 shared-mime-info（OHOS 无）必挂 → 改用 kiconthemes/6.18.0.1（override=True），消费预编译包跳过本地测试。
- conandata.yml 初版带版本号键 `26.04.0:` 导致 get() 关键字展开语法错误 → 改为平铺 url/sha256（klickety 同款）。
- DocTools 适配：先做 patch 文件但上下文行号与 killbots CMakeLists.txt 不匹配 → 改为 build() 内三段字符串替换（移除 `    DocTools`、`add_subdirectory(doc)`、`kdoctools_install(po)`），conandata `patches: {}` 保持空。
- test_package：closure_probe 初版误编为 -shared 导致段错误 → 改为可执行文件；`-Wl,-rpath,d1,d2` 逗号分隔被 ld.lld 误解析 → 改 -L 逐目录传递。
- 结果：conan create 全通过；test_package 鸿蒙非断言测试 2 项真实执行（dlopen libQt6Core 闭包 OK、.codesign 节存在）+ --version 冒烟 PASS；上游 enginetest 链接 KF5KDEGames/KF5::KDELibs4Support 与 KF6 不兼容未执行（klickety 26.04.0 同款处置，BUILD_TESTING=OFF）。

### 对话 #2（2026-10-15 会话：提交前只读审计与整改）

- 审计发现 4 项门禁失败：① conandata.yml url 被 E017 回写为 file:// predl_cache 沙箱路径（PF7 + CI 定时炸弹）；② test_package/closure_probe 编译产物二进制入库；③ patches/0001 死文件（patches:{} 不引用）且 conanfile docstring 仍引用；④ commit message 不符【积分赛】模板。
- 另发现：conan-verify 从未跑成（G1 缺 export_sources/apply_conandata_patches house pattern）；reports/conan-verify-report.md 缺失；worktree 上 finish step7（W2）因分支基线落后 official/main 误报框架变更。
- 整改：conandata.yml 归一官方 https URL；删除 closure_probe/patches 死文件；conanfile.py 补 house pattern（export_sources + apply_conandata_patches，patches:{} 时 no-op）；补软件级 README.md（kblocks 先例：软件级 = README.md + commands.json 两件套）；notes.md 同步（docstring/对话记录/依赖清单三处一致）；commit 重建为【积分赛】规范 message。
- 分支事故：killbots commit 曾误提交到 feat/tqftpserv-1.2（并发会话共享工作区互相切分支）→ worktree 隔离（wt-killbots）完成全部整改与门禁复跑。
- 结果：conan-verify G0/G1/G2/G3 全 PASS（Verdict: PASS）；E017 复核 conandata.yml 保持官方 URL、无 .ghfast-bak 残留。
- 遗留（非阻塞）：W5 存量 E219/E253/E305 字段为空（他包条目既有问题）；Step 8 gen_summary 报 'str' object has no attribute 'append'（仓库既有 infra bug，SUMMARY.md 未动）。
---

**编译结束**: 2026-10-15 18:37
**最终状态**: built

### 对话 #3（2026-10-15 会话：人工审查 rule4 修复——上游测试真实执行）

- 人工审查裁决 FAIL（rule4 上游测试零执行：tests/CMakeLists.txt 注册了 add_test(NAME enginetest)，PR 声明 0/4 不通过）。要求在鸿蒙环境真实执行上游用例。
- 核验上游源码：tests/enginetest.cpp 使用 KF5-only API（KGlobal/KStandardDirs，KF6 已删除 KDELibs4Support）；tests/CMakeLists.txt 链接 KF5KDEGames + KF5::KDELibs4Support；主 CMakeLists.txt 第 62-63 行上游自己注释了 add_subdirectory(tests)（"Reactivate"）——测试为 KF5 遗留死代码，从未进入 release 构建。
- KF6 移植方案（最小兼容 shim，不改测试语义）：
  1. kf5compat_shim.h：KGlobal/KStandardDirs 最小实现（addResourceDir 将 ruleset 目录转发到 QStandardPaths——src/ruleset.cpp 已用 QStandardPaths::locate 加载规则集，KGlobal 调用实为 KF5 死路径）；
  2. 复用主构建树 killbots.dir 的 10 个 .obj（coordinator/engine/renderer/ruleset/scene/sprite/rulesetbase/settings/killbots_debug + mocs）+ 生成头（settings.h/rulesetbase.h/killbots_debug.h），仅新编 enginetest.cpp + moc_enginetest.cpp；
  3. 剔除 QT_NO_CAST_FROM_ASCII 等编码检查宏（上游测试源码从未在该宏下编译，仅影响测试翻译单元，无 ABI 影响）；
  4. 运行环境：offscreen QPA + QT_QPA_FONTDIR=/system/fonts + XDG_DATA_HOME 下部署 data/enginetest/themes（desktop+svgz，KGameThemeProvider 按 AppDataLocation/<appname>/themes 发现主题，FileName=robotkill.svgz 需 gzip 版）+ data/killbots/rulesets。
- 调试记录（SIGSEGV handler + llvm-symbolizer 定位 libKDEGames6.so+0x6e3c8）：主题未发现（count=0）时 KGameRenderer::theme() 对 KGameTheme 元调用空指针崩溃——KGameThemeProvider 按 AppDataLocation/<appname>/themes 查找，测试进程 appname=enginetest，部署对应目录 + 补齐 .svgz 后全链通过。
- 结果：上游 enginetest 真实执行 **419 passed, 0 failed, 0 skipped, 0 blacklisted**（4 个测试函数 testValidCells/testRandomEmptyCell/testMoveIsValid/testMoveIsSafe 全过），exit code 0。日志：killbots-enginetest/enginetest-full.log。
