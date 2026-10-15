# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_82d06cc3.md`

---

## 背景

- **软件名称**: kcachegrind
- **版本**: 26.04.0
- **构建日期**: 2026-10-15
- **构建系统**: cmake
- **上游仓库**: https://download.kde.org/stable/release-service/26.04.0/src/kcachegrind-26.04.0.tar.xz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
- qtbase/6.11.1.1
- kdbusaddons/6.29.0
- kio/6.14.0
- kxmlgui/6.18.0
- kconfigwidgets/6.18.0
- karchive/6.19.0
- openssl/3.5.6.1
- libxml2/2.15.3
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被自动识别为 `autotools`（包内 `po/` 目录干扰），实为纯 CMake，配方按 CMake 手写 |
| build | 编译构建 | 成功 | 构建系统: cmake；`conan create` 32/32 包安装成功 |
| conan-verify | 配方验证 | 通过 | G0 预构建风险 / G1 配方完整性 / G2 干净 `conan create` / G3 系统同名库隔离 / G4 产物完整性；L2 skip（GUI 应用，CI 内置探针无运行环境，已由 test_package 覆盖）、L4 通过、L5 通过 |
| finish | 归档收尾 | 完成 | W2 结构检查 + R36 依赖检查 + W3 本地 CI 全部通过（`KC/JC/L0/L1/L1e/L4/L5=pass`，L2=skip）；`.ci-result.json` 已写入（exit_code=0） |
| submit | PR提交+AI检视+CI | PR #15873 已建、CI 已触发 | 走手册等价路径（见下）；AI Review / 远程 CI 结果待 follow-up 续环确认 |

### 失败与问题

- **1**: 根因=上游链接 `KF6::KIOWidgets`，ohpcd 的 kio/6.26.0 无此库（KIOCORE_ONLY 变体）, 解决方案=改用带 KIOWidgets 的 kio/6.14.0 + `override=True` 把其内部 6.14 钉版整族抬到 6.18 线（ktimer 26.04.0 先例）
- **3**: 根因=**`kcachegrind --version` 退出码 1**，输出 `kf.dbusaddons: DBus session bus not found`, 解决方案=补丁 `0001-kcachegrind-main.cpp.patch`：仅当 `QDBusConnection::sessionBus().isConnected()` 时才构造 `KDBusService`（无平台宏，运行期能力探测）
- **4**: 根因=`doc/` 与 `kdoctools_install(po)` 需要 KF6DocTools, 解决方案=上游 `find_package(KF6DocTools)` 为 `TYPE OPTIONAL` ⇒ 不声明 kdoctools 即由 `_FOUND` 守卫自动跳过，无需补丁
- **5**: 根因=主二进制裸名 `DT_NEEDED`（`libKF6KIOCore.so` 等）在 OHOS musl 下无法解析, 解决方案=`generate()` 用 `-Wl,--disable-new-dtags -Wl,-rpath,<全部依赖 lib>` 写入 **DT_RPATH**（对整棵依赖树生效）
- **6**: 根因=12/27 个 `DT_NEEDED` 是 conan 缓存绝对路径（如 `/storage/.../kxmlg.../p/lib/libKF6XmlGui.so`）, 解决方案=ohpcd 上发布的 KF6 库不带 `DT_SONAME`（E537 族，仓内同族包同形）⇒ 如实记录为已知生态限制，test_package 记 INFO 不判失败，运行期由 DT_RPATH 解析

### 知识图谱使用情况

- **引用知识条目**: E537（KF6 预编译库无 DT_SONAME → 绝对路径 DT_NEEDED）、`DRAFT-conan-version-family-override-uppin`（kio/6.14.0 + 全族 override 升钉）、`DRAFT-ktimer-26.04.0-kf6-tray-dbus-provider-selection`（Qt6DBus 单提供者基座选型）
- **新增知识草稿**: 3 条（本次新生成 1 条：`DRAFT-kcachegrind-26.04.0-kf6-nodbus-service-startup-abort.{kv,md}`）
- **引擎命中情况**: 草稿目录 3517 条
- **测试统计**: 总计 31, 通过 31, 失败 0, 跳过 0
- **未覆盖的错误模式**: `KDBusService 构造期在无 D-Bus 会话总线时终止进程` 此前无任何 E 条目覆盖（ktimer 草稿只覆盖构建期 `USE_DBUS` 选型），本次已落草稿；另一空白是「KF6 GUI 应用 `--version` 冒烟假绿」这一测试方法论缺口——建议在 `docs/TEST_QUALITY_SPEC.md` 的 app 包测试要求中显式写明「GUI 应用必须补 offscreen 功能冒烟，`--version` 不足以证明可用」。

### AI 检视结果

- **检视阶段到达**: Phase 1 (等待摘要)
- **变更摘要评估**: 本会话按 adapt-lib-flow §6「到 PR 即停」执行，未在会话内等待 atomgit-bot 摘要；PR 已创建并触发 CI，续环由 follow-up 完成
- **检视意见数量**: 0（会话内尚未产生）
- **检视意见处理**: 无（待 follow-up 按 `submit --resume` 续环处理）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`KC/JC/L0/L1/L1e/L4/L5=pass`，L2=skip；`L1e: Negative test confirmed — test genuinely depends on kcachegrind`）
- **远程 CI (PR 校验)**: 已通过评论 `/rebuild` 触发（note_id 193840918），会话内未等待结果——**尚未确认通过**，需 follow-up `submit --resume` 续环到绿
- **CI 失败原因**: 会话内无（结果未知）

### 效率分析

- **HANDOFF 次数**: 0 次（`finish` 的 step [3/10] G0 clean-verify 报了一次 `configure exit 127`，但该步骤为非阻塞框架步骤：它按 autotools 口径跑 `./configure`，对纯 CMake 工程不适用；未产生阻塞性 HANDOFF）
- **重试次数**: 3 次 `conan create`（① 首轮暴露 `--version` 因 DBus 退出码 1；② 打补丁后 `--version` 通过；③ 补功能冒烟断言后 31/31 全过）；`kio/6.14.0` 因 override 升族只本地重建 1 次（配方自带 `BUILD_TESTING=OFF`）
- **关键瓶颈**: ① 机器负载极高（多个并发适配会话共用 `~/.conan2` 与 CPU，load average 一度 >60），单次 `conan create` 被拉长到 ~20 分钟；② `init-build` 把构建系统误判成 autotools，生成的三件套模板（conanfile/test_package/MANIFEST）全部不可用，需按 CMake 手写
- **耗时较长的步骤**: `kio` 本地重建（首次 ~12 分钟，受并发负载影响）+ `kcachegrind` 自身编译（3 次全量 ~5-8 分钟/次）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-15T01:18:44 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`init-build` 的构建系统识别要「根构建文件优先」**：本包根目录是 `CMakeLists.txt`，但因包内存在 `po/`（KDE 应用的 gettext 目录，含 autotools 痕迹）被判定为 `autotools`，导致 `conan-init` 生成的三件套模板全部不适用（`conanfile.py`/`test_package`/`MANIFEST.yml` 都按 autotools 生成），必须手写。建议 `lang_detect`/`build_system_detect` 采用与踩坑清单 #21 同款修法：先看根目录构建文件（`CMakeLists.txt`/`configure`/`Makefile`/`meson.build`），再回退子目录扫描；KDE 应用建议直接优先 `CMakeLists.txt`（上游已全部 CMake 化）。
2. **把「依变体开关核依赖」写进 W0**：目前 `preflight_check.sh`/`conan download` 只回答「包+版本是否已发布」，但本项目多次出现「同包同版本、变体不同、能力不同」的坑（`kio` KIOCORE_ONLY vs 完整、`statusnotifieritem` vs `kstatusnotifieritem` 的 `USE_DBUS`、`qtbase` 的 `FEATURE_dbus`）。建议 W0 检查项补一条「识别目标的 CMake 组件需求 → 对照依赖配方 docstring 的变体开关」，或在 `software-registry` 中为这类包登记 `variants` 字段。
3. **`submit` 的 `packaging_present` 自检应在纯 app 包上豁免**：本项目所有 `package_type="application"` 包都必然撞上该恒 FAIL（清单 #14），结果是每单都要手工等价路径 + 手工补 R50 两件套，增加漏项风险。建议按 `package_type` 分支：app 包改为校验 `.staging-verified` + `bin/` 产物。

### 模板改进

1. **CMake + KF6 app 配方缺一份「六件套」骨架**：`ktimer`/`kteatime`/`kcachegrind` 等多份配方在 `generate()` 里逐字重复同样的 5 段代码（`KF_IGNORE_PLATFORM_CHECK` + `KF_SKIP_PO_PROCESSING` + `ECM_MODULE_PATH` + `conan_cmakedeps_paths.cmake` + `-Wl,--disable-new-dtags -Wl,-rpath`），差异只在依赖列表与少量变量。建议新增 `templates/conanfile-kf6-app.py.tmpl`（骨架仓 `backlog` 里已有「KF6 模板」条目，本次再次证实需求）。
2. **app 包 `test_package` 缺 GUI 冒烟模板**：现有 `test_package` 模板是 autotools/CMake 库的 `cmake.test()` 形态，对 GUI app 不适用。建议补 `templates/test_package-app-gui.py.tmpl`：`QT_QPA_PLATFORM=offscreen` + `DBUS_SESSION_BUS_ADDRESS` 占位 + 「运行 `--version`」+「带真实数据文件启动并断言存活/完成一次真实解析」两段式，并默认带上 ELF 断言组。
3. **`SKILL_FEEDBACK` 骨架的自动填充可以更实**：骨架里「执行概要」表的 `conan-verify` 一行留作空白占位，但同一次运行的工具输出里已有 G0–G4/L2/L4/L5 逐项结论（`conan-verify-report.md`）；「CI 结果」的「远程 CI」在尚未出结果时被填成「通过 (PR 校验)」，属自动填充失真（本报告已手工纠正为「尚未确认」）。建议这两个字段改为从 `reports/conan-verify-report.md`、`.submit-state.json` 的真实状态派生，未知就写「未知」。

### 自动化补全

1. **`reports/*.md` 的 force-add 应工具化**：文本报告（`test-report.md`/`pr-body.md`/`conan-verify-report.md`）与 `*.log` 的界线依赖 AI 记忆踩坑清单 #19，本单仍需手工 `git add -f` 逐项挑选。建议 `finish`/`submit` 直接输出「应入库报告清单」，或让 `submit` 自动 force-add 白名单后缀、自动拒绝 `*.log`。
2. **`--no-preflight` 的取证应可复用**：PF9 与 PF8/L0k 在「新包首次入库」场景结构性对立（清单 #15），每单都要手跑 preflight、复制输出、写进 PR 正文。建议 `preflight.py` 增加 `--explain-pf9-software-level` 模式：命中软件级 `README.md`/`commands.json` 时自动生成可直接贴进 PR 正文的取证段落。
3. **`result` 的默认落盘位置在共享机上会互相覆盖**：`$HOME/ohpcd-ai-worker-result.json` 被多会话共用（本机同时有 4+ 个适配会话），必须 `--force` 覆盖，存在互相清掉回执的风险。建议默认落到 `$HOME/ohpcd-ai-worker-result-<OHC_AGENT_ID>.json` 或首次写入即告警并保留 `.bak`。

### 知识图谱覆盖

1. **新增 E 条目（本次已落草稿）**：`KDBusService 在无 D-Bus 会话总线的平台上构造即终止进程` —— 现象 `kf.dbusaddons: DBus session bus not found` + 任何参数下 exit 1；修法=运行期能力守卫 `QDBusConnection::sessionBus().isConnected()`。适用于所有 KDE Gear GUI 应用（大量应用在 `main()` 早期无条件构造该对象）。
2. **建议新增「app 包测试方法论」条目**：`--version` 冒烟对 KF6/KDE GUI 应用会**假绿**（启动期构造副作用发生在参数处理之前或之后，两种布局都可能掩盖真实启动失败）；正确做法是 offscreen + 真实数据文件的**功能冒烟**（本次实测输出 `Selected  "main"` 才证明 loader 真的跑通）。
3. **建议把「变体开关」并入既有依赖家族条目**：`DRAFT-conan-version-family-override-uppin` 已覆盖「家族版本离散 → 低版本配方 + override 升钉」，但未覆盖「同版本不同变体（KIOCORE_ONLY / USE_DBUS / FEATURE_dbus）」这一层；建议在该条目或新建条目中显式写明「判依赖可用性 = 包名 + 版本 + **变体开关**」三元组。

---

## 作者

- **姓名**: ohc-agent
- **邮箱**: ohc-agent@local
- **Agent ID**: F993
- **生成时间**: 2026-10-15 01:18:44
- **PR 编号**: 15873
- **Git Commit**: d8e5fefe37
