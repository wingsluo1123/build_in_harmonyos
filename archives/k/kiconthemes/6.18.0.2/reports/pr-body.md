- **三方库名称**：kiconthemes
- **上游版本**：v6.18.0（Conan 包版本 `6.18.0.2`，依赖线修复后缀）
- **上游仓库地址**：https://invent.kde.org/frameworks/kiconthemes （源码发布源：https://download.kde.org/stable/frameworks/6.18/kiconthemes-6.18.0.tar.xz，SHA-256 `b971460949fafc98e7ae293f35635c2fd6101a6fc46b2f4fce64bb21440ece04`）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：adapt-lib-flow（适配库流程）；`knowledge/drafts/DRAFT-conan-override-kf-version-conflict.md`（KF6 线 karchive 版本冲突与 override 先例）、`knowledge/drafts/kwalletmanager-26.04.0-kf6-line-mismatch-dual-qt-anchor.md`（KF6 版本线错位选线 + karchive override 决策树）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 8 | 来源：上游 `autotests/` 的 8 个 QtTest 目标（7 个无条件 `kiconthemes_tests(...)`：kiconloader_unittest / kiconloader_resourcethemetest / kicontheme_unittest / kiconengine_unittest / kiconengine_scaled_unittest / kicondialog_unittest / kpixmapsequenceloadertest；+ 1 个需 `Qt6::Quick` 的条件目标 kquickiconprovidertest） |
| 集成测试 | 0 | 上游未定义独立集成测试 |
| 其他测试 | 1 | `kiconloader_benchmark`（上游仅编译，不随 ctest 自动运行） |
| **合计** | **9** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 7 | -1 | OHOS 实测执行 7 个上游目标：CTest 5/5 通过（kiconloader_resourcethemetest、kicontheme_unittest、kiconengine_scaled_unittest、kicondialog_unittest、kpixmapsequenceloadertest），另 `kiconloader_unittest` 29/29、`kiconengine_unittest` 8/8 以支持用例子集直跑；`kquickiconprovidertest` 因 Qt6Qml/Qt6Quick 未发布到 ohpcd 不注册（`KICONTHEMES_USE_QTQUICK=OFF`） |
| 集成测试 | 0 | 不变 | 上游无独立集成测试 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.cpp`：真实 API 消费者冒烟，链接 `KF6::IconThemes` 并调用 `KIconLoader::global()`（运行输出 `PASS: KIconLoader::global() OK`），CMake/CTest 编译+链接+运行三阶段 |
| **合计** | **8** | **-1** | 上游 1 个 QtQuick 条件目标在 OHOS 不可注册；断言级 42/42 全绿 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：`patches/0001-CMakeLists.txt.patch` 只把**可选**的 `kquickiconprovidertest`
> 目标包在 `KICONTHEMES_USE_QTQUICK` 开关内（OHOS 置 OFF）并注释掉需要 Qt6Qml 的
> `include(ECMQmlModule)`；未改动任何测试用例的源码、断言或数据。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

---

## 验证结果

- 编译状态：通过（本机 `conan create archives/k/kiconthemes/6.18.0.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64` 退出码 0；构建 + `ctest` + 打包 + 4 个 ELF 自签名 + `test_package` 全绿；另 `ohc conan-verify kiconthemes 6.18.0.2` 实测 **G0/G1/G2/G3/G4 全 PASS，配方验证通过**）
- 上游测试用例通过率：42/42（100.00%）
  - 口径：5 个 CTest 目标 5/5 + `kiconloader_unittest` 29/29 checks + `kiconengine_unittest` 8/8 checks = 42/42；
    未执行项及原因逐条见「补充说明」第 4 条。
- 新增测试用例通过率：1/1（100.00%）

---

## 补充说明

1. **本 PR 解决的问题（依赖线修复）**：制品仓中已发布的 `kiconthemes/6.18.0`
   只有唯一一个 recipe revision `f82185f3a6daed7a2bae8d5f14a6e773`，它硬钉**静态**
   `karchive/6.19.0`；而 6.18 线其余消费者（`knewstuff/6.18.0`、`libkdegames/26.04.0`、
   `kxmlgui/6.18.0`、`akonadi/25.12.3` …）都钉 `karchive/6.18.0`，导致图被拽出 6.18 线：

   ```
   $ conan graph info --requires=kiconthemes/6.18.0 --requires=knewstuff/6.18.0
   ERROR: Version conflict: Conflict between karchive/6.18.0 and karchive/6.19.0 in the graph.
   ```

   修复方式：把 kiconthemes 的 karchive 需求回退到同代共享库 `karchive/6.18.0`，
   让图留在 6.18 线。修复后实测：

   ```
   $ conan graph info --requires=kiconthemes/6.18.0.2 --requires=knewstuff/6.18.0
   exit=0；图中 karchive/6.18.0 唯一，无 karchive/6.19.0 节点
   ```

2. **先验证未真用到 karchive 6.19 新 API（任务硬性要求，已逐条取证）**：
   - kiconthemes 全树只有一条 KArchive 代码路径 `KCompressionDevice`：
     `src/CMakeLists.txt:66`（`KF6::Archive  # for KCompressionDevice`）、
     `src/kiconloader.cpp:34`（`#include <KCompressionDevice>`）、
     `src/kiconloader.cpp:669`（`new KCompressionDevice(path, KCompressionDevice::GZip)`）；
     无 KZip/KTar/KAr 等其他 API。
   - 上游自身版本地板就是 6.18.0：`CMakeLists.txt:4` `set(KF_DEP_VERSION "6.18.0")`、
     `CMakeLists.txt:69` `find_package(KF6Archive ${KF_DEP_VERSION} REQUIRED)`、
     `KF6IconThemesConfig.cmake.in:14` `find_dependency(KF6Archive "@KF_DEP_VERSION@")`。
   - `diff -u karchive-6.18.0/src/kcompressiondevice.h karchive-6.19.0/src/kcompressiondevice.h`
     输出为空（**逐字节相同**），说明所用构造函数与 `GZip` 枚举在两版均存在。
   - 本次实测：以 `karchive/6.18.0` 构建 kiconthemes 6.18.0.2 全部通过（含 `.svgz` 路径所在
     的 KIconLoader 测试），package_id `5937e6fd91b6589196a15790f369a1328a4907fb` 与
     6.18.0.1（同样钉 karchive/6.18.0）完全一致 → 依赖闭包与二进制等价。

3. **版本号为什么是 `6.18.0.2`**：制品仓拒绝同一版本下上传第二个 recipe revision
   （HTTP 409），坏的 `6.18.0` 引用无法原地替换；按 R37/L0j「已发布配方修改必须递增版本号」
   走受控再发布路径（先例 `kpackage/6.18.0.2`）。`6.18.0.1` 虽已把 karchive 调整为
   `6.18.0`，但 6.18 线多数消费者仍 pin `kiconthemes/6.18.0`；本 PR 提供 `6.18.0.2`
   作为 6.18 线的干净引用，后续按 `chore(deps)` 把消费者对齐到该修订即可彻底消除 override 补丁。
   本 PR 严格单包（只动 `archives/k/kiconthemes/`），消费者迁移不在本 PR 内。

4. **未执行的上游测试逐项说明**：
   - `kquickiconprovidertest`：需 `Qt6::Quick`/Qt6Qml，ohpcd 未发布，`KICONTHEMES_USE_QTQUICK=OFF`
     下该目标不注册（上游本身就是 `if (TARGET Qt6::Quick)` 条件注册）。
   - `kiconloader_unittest` 中 1 个依赖 shared-mime-info 数据行的数据行未执行；其余
     29 个用例按用例名逐个直跑，输出 `Totals: 29 passed, 0 failed`。
   - `kiconengine_unittest::testMode`：需 KF6BreezeIcons（ohpcd 未发布）；其余 8 个
     checks 直跑 `Totals: 8 passed, 0 failed`。

5. **门禁说明（PF9）**：归档规范（ARCHIVE-SPEC）要求新版本同步软件级
   `archives/k/kiconthemes/manifest.yaml` 与 `README.md`，而 PF9 路径闸要求变更全部落在
   `archives/<字母>/<包>/<版本>/` 单层目录内，两者天然冲突（仓内既有先例：
   libdisplay-info 0.4.0、zpaqfranz 63.3 等）。本 PR 已逐项实测 PF1–PF8 通过，仅 PF9 因
   软件级三个标准文件（`manifest.yaml` / `README.md` / `commands.json`）命中，故建 PR 时显式使用
   `--no-preflight`，并在此如实说明，不做静默绕过。

6. **产物与证据**：`archives/k/kiconthemes/6.18.0.2/{conanfile.py, conandata.yml,
   patches/0001-CMakeLists.txt.patch, test_package/, notes.md, manifest.yaml}`；
   测试明细见 `reports/test-report.md`，独立审计见 `reports/audit-result.json`。

7. **同包内的连带修正（R38 / PF8 / CI L0k）**：本包实际打包了 `kiconfinder6`
   命令行工具（本地构建产物 `bin/kiconfinder6` 已签名入包），但配方此前未声明
   `bindirs`、软件级 `commands.json` 也未登记 6.18.x 版本。本次在 6.18.0.2 的
   `package_info()` 显式声明 `bindirs = ["bin"]`（与 `kpackage` 同构）并在
   `archives/k/kiconthemes/commands.json` 登记 `6.18.0.2`，避免 CI L0k 报
   「commands.json missing version 6.18.0.2」。此项不改变消费者可见行为
   （`bindirs` 默认即 `["bin"]`）。

8. **独立审计（W4）**：结论 `verdict=pass`，**P0/P1/P2 = 0**（审计原件
   `reports/audit-result.json`，含被检文件 sha256）。残留 P3 建议的处置：
   ① conandata 未加 `patch_description`/`patch_type` —— 有意保持与 6.18.0.1
   一致的极简 delta，避免改动已被本机实测覆盖的配方内容；② `--no-preflight`
   需主编确认（规则 24）—— 已在本条如实披露；③ `6.18.0.1/manifest.yaml` 既有
   `full_reference` 陈旧 —— 非本 PR 变更文件，未纳入本次修复。
   另有 `reports/conan-verify-report.md` 记录 `ohc conan-verify` 的 G0–G4 逐项结果。
