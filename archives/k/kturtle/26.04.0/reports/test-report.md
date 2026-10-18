# kturtle 26.04.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 device
- Clang 15 (project-bundled, /data/service/hnp/bin/clang)
- Conan 2.x (OHOS-adapted), profile ci/conan/profiles/ohos-aarch64

## Verification

- `bash ci/scripts/preflight_check.sh kturtle/26.04.0`: 依赖链 28 包全部在仓
  （W0 阶段逐包 `conan download --only-recipe` 实证）
- `python3 scripts/ohc-run.py conan-verify kturtle 26.04.0`: exit 0
  (G0/G1 recipe completeness / G2 clean `conan create` / G3 系统同名库隔离 /
   G4 产物完整性 + L2 smoke / L4 checksec / L5 基线 all PASS)
  G2 全新编译后 test_package 真实执行：
  `OK: bin/kturtle --help executed cleanly (Qt6/KF6 closure loaded, KAboutData usage printed)`
- `python3 scripts/ohc-run.py finish kturtle 26.04.0 published`: W3 本地 CI 模拟通过
  （setup.sh + build_and_test.sh，JC 增量模式 PASS，`.ci-result.json` `exit_code=0`）
- 依赖图：qtbase/6.11.1 全图归一 + KF6 6.26.0/6.18.0 系（override 口径见
  conanfile.py requirements() 注释），无 qtsensors 类缺口

## Upstream tests

上游（KDE Gear kturtle 26.04.0）**无测试套件**：全树无 `autotests/`/`tests/`
目录，顶层与 src CMakeLists.txt 无 `enable_testing`/`add_test`/`ecm_add_test`/
`BUILD_TESTING` 任何注册（`scripts/if-test.turtle` 是 Turtle 语言演示脚本，
非测试）。按 R51 如实申报 `upstream_tests: []`，不虚构命令。

## test_package

真实执行被测包交付物（R34，非空壳）：

1. 打包完整性断言：`bin/kturtle` 存在 + `share/applications/org.kde.kturtle.desktop`
   + `share/knsrcfiles/kturtle.knsrc` + `share/metainfo/org.kde.kturtle.appdata.xml`
   （证明 install 阶段交付了完整应用而非裸二进制）。
2. 真实执行 `bin/kturtle --help`（offscreen QPA、私有 HOME/XDG_RUNTIME_DIR）：
   加载全 Qt6/KF6 链接闭包（KIO/NewStuff/TextWidgets/XmlGui/Crash/I18n/
   CoreAddons + Qt6 Svg/SvgWidgets），KAboutData 用法输出含 `kturtle` 与
   usage/options，进程退出码 0（KDE KAboutData 应用在进入 GUI 主循环前
   处理 --help，可确定性收尾；60s 挂起保护）。

- Test cases: 2
- Passed: 2
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
publication. 知识库拓展四件套（knowledge-extension/）同 PR 附带：
detect / repair / README / reproduce 四件均实测（体检 C=9 → fill → C=0 闭环；
reproduce 两阶段矩阵 rc=0），知识草稿
`knowledge/drafts/hmdfs-signed-elf-byte-rewrite-exec-denied.{kv,md}`。
