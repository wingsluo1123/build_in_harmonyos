# freedesktop 守护进程型组件 library-only 裁剪 + 测试分口径全量申报

> Draft: `DRAFT-MODEMMANAGER-1242-DAEMON-GATE-TESTS-SPLIT`
> Stem: `modemmanager-1.24.2-daemon-bool-gate-lib-only-tests-split` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MODEMMANAGER-1242-DAEMON-GATE-TESTS-SPLIT
- **严重度**: 2
- **类别**: build|packaging|testing
- **触发工具**: conan|ci
- **阶段**: build

## 错误特征

library-only 交付 freedesktop 守护进程型组件时两类典型失败：

```
# 直接构建 daemon（无开关可关）：
ERROR: dependency "libgudev-1.0" not found      # OHOS 无 udev/libgudev
meson.build:XXX:ERROR: polkit not found          # OHOS 无 polkit

# 只关 daemon 但开测试（未扩展门控）：
src/... 未进构建图，但顶层 test/meson.build 引用
libhelpers_dep / libkerneldevice_dep / libport_dep
meson setup: ERROR: Unknown variable "libhelpers_dep".   # configure 直接崩

# 测试整体禁用 + PR 正文只申报子集：
rule4 FAIL: 上游实测 N=377 > 声明 N=71（少报，审查按全仓
g_test_add_func 注册数清点，与提交者申报口径不一致）
```

## 根因

freedesktop 系"守护进程+客户端库"双层组件（ModemManager = daemon + libmm-glib，
NetworkManager = daemon + libnm）在 OHOS 上只能交付客户端库：daemon 运行期硬依赖
D-Bus 系统总线、udev+libgudev、可选 libmbim/libqmi/libqrtr、systemd
journal/suspend-resume、polkit 与厂商插件栈——OHOS PC 均无。但上游 meson.build
无条件 `subdir('src')`/`subdir('cli')`，没有开关。

且上游测试结构与 daemon 耦合：
- 顶层 `test/` 程序链接 **src/meson.build 内部声明**的 libhelpers_dep/
  libkerneldevice_dep/libport_dep——library-only 构建下这些变量未定义，
  `-Dtests=true` 直接 configure 报错；
- `tools/tests` 经 test-wrapper.sh 在 meson test 阶段拉起 D-Bus 会话总线跑 stub。

若因此 `-Dtests=false` 整体禁用并在 PR 正文只申报子集（如 libmm-glib/tests 71），
审查复扫按全仓 `g_test_add_func(` 注册数实测（ModemManager 1.24.2 = 377 =
libmm-glib/tests 69 + src/tests 143 + src/plugins 165）即命中 rule4 少报。

## 推荐方案

**方法**: `neutral-bool-gate-patch-plus-tests-split-census`

1. **中性布尔门控补丁**：顶层 meson.build 加 `-Ddaemon` 布尔选项（默认 true，
   上游行为不变）；`-Ddaemon=false` 时跳过 src/、cli/、examples/，并在**顶层**生成
   原本由 src/meson.build 生成的 headers-only pkg-config（ModemManager.pc——
   libmm-glib.pc 的 requires 引用它，不补则下游 pkg-config 断链）。
2. **关键增量——门控扩展到 daemon 侧测试目录**：把顶层 enable_tests 块里的
   `test/` 与 `tools/tests/` 一并门控进 enable_daemon，使 `-Dtests=true` 在
   library-only 构建可用，只配置离线套件（libmm-glib/tests、libqcdm/tests）。
3. **配方启用测试并真跑**：`-Dtests=true` + build() 阶段 `Meson(self).test()`
   （即 `meson test -v`）；为测试注入运行环境——LD_LIBRARY_PATH 前置
   `build_folder/libmm-glib`（刚构建的 so）+ 依赖 libdirs（conan glib）。
4. **PR 正文统计表改全仓 N 分口径**：N = 全仓 g_test_add_func 注册数（与审查
   同口径），分解"可离线 X + 需 daemon 环境 Y"；X 真跑 PASS，Y 逐类定性豁免
   （带"环境限制"关键词）；合计行 + 鸿蒙特有测试行（test_package 消费者用例
   即鸿蒙特有测试，rule12 过闸）。
5. **验证结果段同口径**：上游通过率 X/N（离线子集 X/X=100% + 豁免说明）。

## 实测数据（ModemManager 1.24.2，PR #14799）

- 全仓 `g_test_add_func(` = **377**：libmm-glib/tests 69 + src/tests 143 +
  src/plugins 165（另 tools/tests 2 例走 `g_test_add` 宏、test-modem-helpers.c
  182 例走 `g_test_suite_add` 宏、libqcdm 36 例自定义 TESTCASE 宏，均口径外）
- 离线真跑：`meson test` 3/3 OK（Ok:3 Fail:0）——test-common-helpers TAP
  `1..68` 全 ok + test-pco `1..1` ok（+口径外 libqcdm 离线 12 例全 ok）
- test_package：13/13 PASS（`ALL 13 CHECKS PASSED`）
- 308 例 daemon 环境豁免分类：src/tests 143（链 daemon 内部静态库+PTY/udev）、
  src/plugins 165（15 厂商插件栈）、test/ 6 程序（真实 TTY）、tools/tests 2
  （D-Bus 会话总线）——均因 `-Ddaemon=false` 不进构建图，构建期整体豁免

## 验证命令

```bash
grep -rhoE 'g_test_add_func[[:space:]]*\(' <src> --include='*.c' | wc -l
# 377 —— 全仓 N 清点（rule4 审查同口径）
conan create archives/m/modemmanager/1.24.2 \
  -pr:h=~/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2
# meson test 段：Ok: 3 Fail: 0；test_package: ALL 13 CHECKS PASSED
```

## 取证记录

- 包: modemmanager 1.24.2（archives/m/modemmanager/1.24.2）
- 修复 commit: 0cdf5d86909b（0001 补丁 v2 + conanfile 启用测试）
- CI: #91892 通过（OpenHarmonyPCDeveloper-CI-012）
- 同族组件对: networkmanager 1.58.1（PR #14838，libnm-only 同模式）
