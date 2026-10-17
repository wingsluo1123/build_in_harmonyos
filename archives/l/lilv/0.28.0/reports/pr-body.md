- **三方库名称**：lilv（LV2 插件宿主库，drobilla/lv2 生态）
- **上游版本**：0.28.0
- **上游仓库地址**：https://download.drobilla.net/lilv-0.28.0.tar.xz（sha256 8dcb70ad...，drobilla 官方发布源）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（meson 直驱交叉构建 + pkg-config 两步法 + 依赖钉版互斥同族解法，前置 sratom PR #15450）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 21 | test/meson.build unit_tests 数组（bad_port_index, bad_port_symbol, classes, discovery, get_symbol, no_author, no_verify, plugin, port, preset, project, project_no_author, prototype, reload_bundle, replace_version, state, ui, util, value, verify, world），共享 lilv_test_utils.c 夹具与 test_plugin.lv2 bundle |
| 编译期探针 | — | headers/lint 目录（非断言用例，单列） |
| **合计** | **21** | 清点证据见 reports/test-report.md §一 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 21 | 不变 | 全部保留（配方 -Dtests=disabled 保持库配方纯净，实跑走离线三步法） |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test_lilv_discovery.c：LV2_PATH 指向内嵌 fixture bundle → 包内 liblilv-0 真实执行 world_load_all → 插件发现 → Turtle 解析 → introspection 逐字段断言（doap:name / 端口数 3 / 端口符号 in/out/gain），非纯断言 |
| **合计** | **22** | **+1** | 上游 21 全部保留实跑 + 鸿蒙特有 1 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（探索期零源码修改，conandata.yml 无 patches 声明）
- 上游测试未挂进配方常规构建（-Dtests=disabled），实跑为离线三步法逐用例执行（LD_LIBRARY_PATH=build + conanrun 环境）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有 21 个注册单元测试；新增 1 项鸿蒙特有消费者测试（真实插件发现链路，经 liblilv-0 + serd/sord/sratom 完整 Turtle 解析链）

## 验证结果

- 编译状态：**通过** — conan create 干净构建成功（liblilv-0，OHOS aarch64）；conan-verify G1/G2/G3 + L2/L4/L5 全绿
- 上游测试用例通过率：**21/21（100%）** — 逐用例 rc=0（构建目录 [130/130] 零失败含全部测试二进制），证据见 reports/test-report.md §二
- 验证命令与结果：`conan create` → test_package 输出 `INFO: discovered http://example.org/consumer-test-plugin / INFO: name = "Consumer Test Plugin" / PASS: lilv consumer test`；`conan-verify` → `✅ 配方验证通过: lilv 0.28.0`
- 新增测试用例通过率：**1/1（100%）**
- 依赖：sratom/0.6.22（前置 PR #15450）+ sord/0.16.22 + lv2/1.18.11-git（制品仓已发布；不显式钉 serd——sord 传递钉 serd/0.32.9，显式钉版冲突实证见 notes.md）

## 补充说明

1. 本包为 jalv 1.10.0 适配的依赖链第二步（R36 拓扑序：sratom → lilv → jalv），jalv PR 引用 `lilv/0.28.0`
2. meson 直驱交叉构建：--default-library 表达库形态；特性裁剪 bindings_py/cpp、docs、tools、dynmanifest 全 disabled；pkg-config 两步法（落盘 flags 文件再读回，嵌套 $() 子 shell 在沙箱不稳）
3. 消费者测试所有权陷阱记录：lilv_port_get_symbol 返回 const LilvNode* 由 port 持有，free 即 SIGSEGV（lilv.h 所有权文档 + 实测定位）；0.28.0 无 plugin_get_symbol_by_index，端口符号经 get_port_by_index + port_get_symbol 两步取
4. 无平台宏（PF5/PF6 合规）；编译器经 tools.build:compiler_executables conf（R33）；源 URL 为 drobilla 官方发布站（PF7）；W4 审计 pass（P0/P1=0，2 P2 已修复：destdir 下探失败硬校验、cpp_info.requires 依赖转发；3 P3 已修复/核实）；复审 P3 已修（消费者测试三处致命前置条件改 REQUIRE 早退，NULL 时给 FAIL 行而非 SIGSEGV；cpp_info.requires 修正为 dep::dep 形态——裸包名会被 conan 按内部 component 校验并报错，CI #93033 实证）
5. conan-verify 报告中 G0 "构建系统 unknown" / G4 "无法找到程序包 ID" 为门禁工具对 meson 直驱形态识别不全的告警，非阻断——G2 conan create 成功即实质验证（notes.md 末节，同 sratom 口径）
