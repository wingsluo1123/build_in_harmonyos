# lskat 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（CMake + ECM + Qt6/KF6；**不是** autotools）
- 编译日期: 2026-10-18
- 编译器: clang 15 / libc++（aarch64-linux-ohos，Release）
- 状态: built（conan create + test_package 通过，未 upload）
- 上游源码: https://invent.kde.org/games/lskat/-/archive/v26.04.0/lskat-v26.04.0.tar.gz
  （sha256 `229960a95bb4f8ad80086fe6e44b28ab20c816e095f3a03a5d0863fc81613563`，1,471,986 B）
- 专属工作区: `ran_workspace/_dep_batch_20261018d/lskat-26.04.0/`
  （仓库克隆 `buildb/repo`，分支 `feat/lskat-26.04.0`，从 `origin/main` e52fd432b2 切出）

## 上游形态（26.04.0 tarball）

- Qt6 6.5+/KF6 6.0+ CMake 工程；`find_package(Qt6 ... Gui Svg Widgets)` +
  `find_package(KF6 ... Config CoreAddons Crash DBusAddons DocTools GuiAddons
  I18n WidgetsAddons XmlGui IconThemes)` + `find_package(KDEGames6 6.0.0 REQUIRED)`。
- 一个可执行文件 `lskat`（QApplication + KXmlGui 主窗口，牌桌用
  QGraphicsWidget/QGraphicsScene 绘制），`src/fromlibkdegames/` 内 vendored
  了 4 个卡牌辅助文件（cardcache/carddeckinfo/kcarddialog/kgamecardselector.ui）。
- 数据资产：`themes/`（oxygen/blue/egyptian，SVG→SVGZ 由
  `cmake/InternalMacros.cmake::generate_svgz` 生成，7Zip 缺失时回退
  `gzip -9 -n -c`）、`icons/`（hicolor PNG）、`sounds/`（上游任何 CMakeLists
  都没有 install 规则，保持上游行为不打包）、`org.kde.lskat.desktop` +
  appdata、`doc/`（DocBook handbook）。
- **上游无测试套件**（R51 清点，证据见 `reports/test-report.md`）：
  `find . -maxdepth 2 -type d \( -name test -o -name tests -o -name autotests \)`
  无输出；`grep -rn "add_test\|enable_testing\|ecm_add_tests\|BUILD_TESTING"
  --include=CMakeLists.txt .` 无命中（exit 1）；`.kde-ci.yml` 只有
  `Options: require-passing-tests-on: ['Linux','FreeBSD','Windows']`。

## 编译步骤

```bash
# 0) W0 依赖预检（上一阶段）：24 项依赖 conan download --only-recipe -r=ohpcd 全部 EXIT=0
# 1) 源码核验：invent.kde.org tag v26.04.0 tarball + sha256
# 2) 语言预检：任务语言 cpp / 源文件主体 C++（QApplication、*.cpp/*.h）
# 3) 配方编写：archives/l/lskat/26.04.0/{conanfile.py,conandata.yml,patches/,test_package/}
# 4) 实际构建（与 CI 同参数）
conan create archives/l/lskat/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 5) 配方门禁：python3 scripts/ohc-run.py conan-verify lskat 26.04.0   → G0-G4/L2/L4/L5 PASS
# 6) 收尾：python3 scripts/ohc-run.py finish lskat 26.04.0 built
```

## 首个真实错误与修复

| # | 现象 | 根因 | 修复 | 复验 |
|---|---|---|---|---|
| 1 | `conan graph info` → `WARN: There are some error(s) in the graph: Missing packages: kiconthemes` | ohpcd 上 `kiconthemes/6.18.0` 的已发布二进制依赖 `karchive/6.19.0`，而 `knewstuff/6.18.0` 要求 `karchive/6.18.Z`；配方按 libkdegames 闭包 `karchive/6.18.0 override=True` 后 kiconthemes 无匹配二进制 | 改用 `kiconthemes/6.18.0.1`（该修订按 `karchive/6.18.Z` 构建）+ `override=True` | `conan graph info` 0 missing（62 节点），`conan create` 通过 |
| 2 | `finish` → `L0 quality gate failed: commands_json_r38` | 包类型是 application（`bindirs=['bin']`），R38/L0k 要求软件级 `commands.json` | 新增 `archives/l/lskat/commands.json`（type=tool，ref=lskat/26.04.0） | L0 通过 |
| 3 | `finish` → `JC5: 10 个 archives 下未登记的隐藏文件`（含 main 上已提交的 `.staging-verified`） | W3 的 junk 检查在无 commit 时回退 full 模式（`git ls-files`），扫到**他人历史遗留**的隐藏文件 | 按 CI 语义用 PR diff 模式（`JUNK_PR_DIFF`）+ 单包范围 | JC 检查只看本包 |

## 平台适配要点

1. **DocTools 裁剪**（patch 0001）：移除 KF6 `DocTools` 组件、`add_subdirectory(doc)`、
   `kdoctools_install(po)`；handbook 不是运行期依赖（kblocks/kfourinline/kbreakout 先例）。
2. `KF_IGNORE_PLATFORM_CHECK=TRUE`：OHOS 不在 KDE 平台白名单。
3. `KF_SKIP_PO_PROCESSING=ON`：跳过 po 编目（不需要 gettext msgfmt 工具链）。
4. `-Wl,-z,max-page-size=0x1000`：OHOS musl 加载器拒绝 lld 默认 0x10000 的多 RW LOAD 布局。
5. `package()`：11 条 path-form `DT_NEEDED` 原地改写为裸 basename（.dynstr 等长改写），
   随后用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1` 重签名
   （OHOS 对未签名/被改动 ELF 拒绝 exec）。
6. `ECM_MODULE_PATH` + `conan_cmakedeps_paths.cmake` 手工写（qtbase/KF6/libkdegames 用
   `cmake_find_mode=none`，CMakeDeps 不会把 lib/cmake 放进 CMAKE_PREFIX_PATH）。

## 验证结果

- `conan create`：成功；26 个编译单元，仅 2 处上游 `-Woverloaded-virtual` 告警
  （`src/mainwindow.h:152/158`），无错误、无需除 patch 0001 之外的源码改动。
- `test_package`：6 用例 / 8 断言全通过（0 失败 0 跳过），日志 `reports/conan-create.log`。
- 产物：`bin/lskat`（23 条 NEEDED 全为 basename，4 个 LOAD 段，含 `.codesign`），
  `share/lskat/themes/*`、`share/icons/hicolor/*`、`share/applications`、`share/metainfo`、
  `share/qlogging-categories6`。包大小 4.1 MB。

## 已知限制

- 本机无显示/音频环境：只验证「ELF 加载 + 完整 DT_NEEDED closure 解析 + KAboutData/命令行
  + OHOS 签名/架构门禁」，牌桌渲染、鼠标/键盘输入、音效需真机人工确认（R40）。
- 启动需 D-Bus session（`KDBusService` 初始化失败时进程退出码 1，属环境缺失而非链接失败）。
---

**编译结束**: 2026-10-18 14:59
**最终状态**: built
