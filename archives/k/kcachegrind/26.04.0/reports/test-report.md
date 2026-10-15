# kcachegrind 26.04.0 验证报告（test-report）

## 环境

- HarmonyOS PC aarch64（OpenHarmony，`os=OHOS`、`os.version=6.0`、`arch=armv8`）
- clang 22.1.8 / clang++，Conan 2.29.1（OHOS 适配版）
- profile：`ci/conan/profiles/ohos-aarch64`（host + build 同一 profile）

## 上游测试清点（R51 第一步）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 测试文件 | `find kcachegrind-26.04.0 -iname '*test*'` | 0 个 |
| 测试目录 | `ls -d tests autotests unittests` | 不存在 |
| CMake 测试目标 | 全部 `CMakeLists.txt` grep `add_test\|enable_testing\|BUILD_TESTING` | 0 次命中 |
| 结论 | — | **上游确无测试套件，N_static = 0**（附清点证据于 `test_package/MANIFEST.yml`） |

按 R51 第三步，消费者视角验证由 `test_package/test_kcachegrind.py` 承担
（适配后补全 3 个消费者用例，共 **35** 条断言，含一个完整端到端消费者用例）。

## 验证结果

| 项 | 结果 |
|---|---|
| `conan create`（clean build，32/32 包安装） | ✅ 通过（含 test_package） |
| G0 预构建风险评估 | ✅ 通过 |
| G1 配方完整性 | ✅ 通过 |
| G2 conan create 干净构建 | ✅ 通过 |
| G3 系统同名库隔离 | ✅ 通过（无系统同名库交付物） |
| G4 产物完整性（bin/kcachegrind + 5 转换脚本 + desktop/appdata 元数据） | ✅ 通过 |
| L0 结构性门禁（含 L0k `commands.json` 校验） | ✅ 通过（`L0_RESULT=pass: all checks passed`） |
| L1 test_package 执行 + L1e 破坏性反向验证（R34） | ✅ 通过（`L1e: Negative test confirmed — test genuinely depends on kcachegrind`） |
| L2 CI 内置 smoke 探针（对 `bin/*` 逐个跑 `--version`/`--help`） | ⚠️ skip（5 个转换脚本需要 perl/php/python 运行时；`kcachegrind` 为 GUI 应用，CI 内置探针无运行环境。**已由 test_package 覆盖**：offscreen `--version` + 真实加载 Callgrind trace，见下） |
| L4 安全扫描（补丁规范/危险函数） | ✅ 通过（`L4_RESULT=pass: patches clean`） |
| L5 产物基线（`bin/` 非空） | ✅ 通过（`L5_RESULT=pass: bin/ has content`） |
| KC / JC（知识合规 / 垃圾文件） | ✅ 通过（`KC_RESULT=pass` / `JC_RESULT=pass`） |

## test_package 实测

按「用例」组织（rule12 口径：鸿蒙特有测试必须含**至少一个完整消费者用例**
——真正跑通功能/流程的端到端用例，纯断言不算）：

| 用例 | 类型 | 断言数 | 结果 |
|---|---|---|---|
| CASE 1 运行期冒烟（offscreen `--version`，依赖经 conanrun+DT_RPATH 解析） | 集成测试 | 2 | ✅ |
| **CASE 2 完整消费者用例：Callgrind 剖面分析端到端流程** | **鸿蒙特有测试** | 8 | ✅ |
| CASE 3 产物布局 + OHOS ELF 专项校验 | 鸿蒙特有测试 | 25 | ✅ |
| **合计** | — | **35** | **35/35 通过，0 失败 0 跳过** |

CASE 2 的四段式（`test_package/test_kcachegrind.py`）：

| 阶段 | 内容 |
|---|---|
| **构造输入** | 内嵌**确定性** callgrind 语料：`main`(自身 220) → `parse_trace`(900) → `build_model`(980)，`summary: 2100`；对照语料 `e2` 结构完全相同、**仅入口函数改名**（去掉 `main`）；每次运行给一个可写 `XDG_CONFIG_HOME`（无随机、无外部下载） |
| **真实执行** | offscreen 启动安装后的 `bin/kcachegrind <trace>`，走完整产品链路：进程启动 → Qt6/KF6 平台与 UI 初始化 → loader/插件发现 → 解析 callgrind → 构建 TraceData/CostItem 模型 → 函数视图/调用图选中入口函数 → 超时后终止（证明存活）/ 退出时写回 KConfig |
| **产出结果** | ① stderr 的 `Selected  "<fn>"`；② `<XDG_CONFIG_HOME>/kcachegrindrc`（实测 `[Layouts] Count=1 Current=0`）；③ 进程存活状态；④ stderr 是否含 loader/symbol 错误 |
| **校验内容** | ① 产品选中的函数 == **独立 Python 参考实现**（自带 callgrind 文本解析、不依赖产品代码）算出的入口函数（`main`）；② 参考实现的总自身开销 == 语料自带 `summary:` 声明（2100，交叉验证参考实现本身）；③ **对照语料**（入口改名）不再选中 `main` ⇒ 选中由输入驱动、非硬编码；④ `kcachegrindrc` 写出且含 `[Layouts]` ⇒ KConfig 读写流程真实走通；⑤ 两次运行均无 `Error loading shared library`/`symbol not found`；⑥ 主语料运行期间 GUI 存活 30s 未崩 |

CASE 3 明细：交付物布局 9 条（`bin/kcachegrind` 存在且可执行、5 个 callgrind
转换脚本、desktop 与 appdata 元数据）+ OHOS ELF 16 条（`readelf` 可用性、
PIE(ET_DYN)、GNU_STACK、DT_RPATH、13 个关键 KF6/Qt6 依赖链接断言）= 25 条。

## 已知限制

- 12/27 个 `DT_NEEDED` 为 conan 缓存绝对路径：ohpcd 上发布的 KF6 库不带
  `DT_SONAME`，OHOS 的 CMake 平台不认 `VERSION/SOVERSION`，ld 只能按链接行的
  绝对路径记录（E537 族）。仓内同族包实测同形（kbreakout、kcolorchooser、
  kio 的 `ktelnetservice6`、kcoreaddons 的 `kiconfinder6`），非本配方缺陷；
  `generate()` 注入的 DT_RPATH 覆盖全部依赖 lib 目录，运行期可解析（35/35 断言
  含真实 GUI 加载 trace 均通过）。
- `KF_SKIP_PO_PROCESSING=ON`：包内不含 `.qm` 翻译目录（msgfmt/lconvert 在本平台
  不可用），界面回落英文，非功能缺陷。
- 在线手册（`doc/`、`kdoctools_install(po)`）未构建：上游 `KF6DocTools` 为
  `TYPE OPTIONAL` 可选依赖，由其 `_FOUND` 守卫自动跳过。
- 转换脚本（`bin/*2calltree`）需要 perl/php/python 运行时装机环境，非本包职责。
- **KF6 依赖库的「坏 `DT_NEEDED`」**：CI 首轮真实失败（构建 #92573，26/31）为
  `Error loading shared library ../../bin/libKF6ConfigCore.so (needed by …/libKF6ConfigGui.so)`
  与 `../../bin/libKF6IconThemes.so (needed by …/libKF6IconWidgets.so)`。根因是含 `/`
  的 `DT_NEEDED` 被加载器按**相对 CWD 路径**直接打开（绕过 DT_RPATH/LD_LIBRARY_PATH），
  而 CI worker 缓存里的 kconfigwidgets/kiconthemes 是上游配方在 worker 上本地重建出来的
  同 package_id 副本（Conan 不校验同 package_id 的字节一致性），记录了生产者的
  `../../bin/<lib>.so`；本开发机 `~/.cache/conan2` 恰好存在且副本为发布方构建（绝对路径），
  故本地不暴露。`test_package/conanfile.py` 的 `_reconstruct_kf6_rpaths()` 按
  kteatime/ktimer 26.04.0 先例把依赖 `.so` 复制到 `<conan_cache>/bin` 并以
  `<conan_cache>/recon/kcg` 为 CWD 运行测试（机制已用自造 ELF 实验复现并验证）。
- 远端 CI 前 6 次尝试均为基础设施故障（worker 进程 spawn 耗尽
  `posix_spawn failed: Resource temporarily unavailable` / `/bin/sh: Resource temporarily unavailable`，
  以及 worker 挂死 `mkdir` 超时 1200 s），与本包配方无关。

## 结论

✅ 配方在 HarmonyOS PC aarch64 上可复现构建（干净 `conan create`），
消费者 3 个用例 / 35 条断言全部通过（**含完整端到端消费者用例**：确定性 callgrind 语料 → offscreen 真实运行产品 → `Selected "main"` 与独立 Python 参考实现一致、对照语料反向验证、KConfig 写回）；
CI 首轮暴露的 KF6 相对 `DT_NEEDED` 加载缺陷已按仓内先例修复并本地复验；
状态 `built`（待发布流水线 upload / 远端 CI 复审）。
