- **三方库名称**：raptor2（Raptor RDF Syntax Library）
- **上游版本**：2.0.16
- **上游仓库地址**：https://download.librdf.org/source/ （官网 https://librdf.org/raptor/）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent；命中并复用 E007/E072/E122/E160（autotools HarmonyOS 三元组）、E011/E114/E129/E206（umask 077 临时目录）、E232（Conan+Autotools CONFIG_SHELL）、E524（依赖注入私有 prefix）；本次新增草稿 E550/E551

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 19 | 来源：`src/Makefile.am` 的 automake `TESTS` 程序（含 RDFXML 条件追加的 2 个） |
| 集成测试 | 1233 | 来源：`tests/` 下 13 个子套件（rdfxml、turtle、turtle-2013、ntriples、ntriples-2013、nquads-2013、trig、mkr、grddl、rdfa、rdfa11、json、feeds）的 `check-local` 数据驱动检查项 |
| 其他测试 | 0 | 上游无其它注册测试 |
| **合计** | **1252** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 19 | 不变 | 未增删上游用例 |
| 集成测试 | 1233 | 不变 | 未增删上游用例 |
| 鸿蒙特有测试 | 2 | 新增 | 针对鸿蒙平台特性的测试 |
| **合计** | **1254** | **+2** | |

> **鸿蒙特有测试**：2 个完整消费者端到端用例，在鸿蒙 PC 目标机（HarmonyOS / HongMeng Kernel 1.12.0 / aarch64，原生构建 build==host，clang 15.0.4）由 `conan create` 的 `test_package` 实际执行并 PASS：
> - 用例 ID **R12-01**（库 API 端到端）：源码 `test_package/test_raptor2.c`；输入 `test_package/data/sample.ttl` 与 `test_package/data/sample.rdf`；流程＝用安装后的 `libraptor2` 分别解析 Turtle 与 RDF/XML，各自经 `raptor_new_serializer("ntriples")`/`raptor_serializer_start_to_string` 序列化，排序后逐行比较并核对 3 条预期语句；实际命令 `"<cpp.build.bindirs[0]>/test_raptor2" "<data-dir>"`；退出码 0，输出 `parsed … sample.ttl (3 triples) and … sample.rdf (3 triples)` / `all 3 expected statements present (Turtle == RDF/XML)` / `RESULT: PASS`。
> - 用例 ID **R12-02**（已安装 CLI 端到端）：入口 `test_package/conanfile.py::test()` 第二步；输入 `data/sample.rdf`；流程＝执行包内 `bin/rapper -q -i rdfxml -o ntriples data/sample.rdf` 并断言实际输出的 3 条 N-Triples 语句；输出 `rapper CLI produced all 3 expected statements`。
> - 证据位置：`archives/r/raptor2/2.0.16/reports/test-report.md`（§1.2 逐项记录目标机、命令、退出码与输出核对）；原始运行日志按仓库范围要求保存在本机，未随 PR 提交。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] 否，上游已有测试用例覆盖
- [x] **否**，上游已有完整测试用例覆盖（`make check`：19 个 `src/` 单测程序 + `tests/` 13 个语料子套件）；适配后新增的 2 个用例是**鸿蒙消费者端到端用例**，已计入上表「鸿蒙特有测试」行，不属于"上游无测试而补全"

## 验证结果

- 编译状态：**通过**（`conan create archives/r/raptor2/2.0.16 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -r=ohpcd`，退出码 0）
- 上游测试用例通过率：**1224/1252（97.8%）**
  - `src/` 单测：19/19 PASS（`src/test-suite.log`：`# TOTAL: 19 / # PASS: 19 / # FAIL: 0`）
  - `tests/` 语料：1233 项中 1205 项 PASS；其余 **28 项与上游 `Makefile.am` 中的 `EXPECTED_FAILURES` 清单逐字一致**（`tests/rdfa` 4 项、`tests/rdfa11` 24 项），harness 打印 `Ignoring expected failures` 并令 `result=0`——属上游声明的预期失败，非适配引入，全部 28 项均未修改、未删除
  - `make check` 整体退出码 **0**；适配导致的失败项 **0**
- 新增测试用例通过率：**2/2（100%）**（鸿蒙特有测试 R12-01、R12-02，目标机实测）

## 补充说明

**依赖（均已发布并实测有 binary）**：libxml2/2.15.3.1、libxslt/1.1.45.2、yajl/2.1.0、curl/8.22.0、icu4c/78.3；`libxslt` 声明的 libxml2/2.15.3 以 `override=True` 统一到 2.15.3.1。

**功能开关**：保持上游全部 10 个解析器与 11 个序列化器启用（含 GRDDL 需 libxslt、RDF/JSON 需 yajl、WWW 后端用 libcurl、NFC 校验用 ICU）；配方内 `_assert_full_feature_set()` 对 19 个条件特性宏做构建期断言，任一缺失即构建失败，避免"编译通过但静默裁功能"。

**5 个适配补丁**（均由 `ohc-run.py refresh-patch --auto` 生成，`patches/` 新增行无平台宏，PF5 干净）：
1. `0001-build-config.guess.patch` — config.guess 增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`
2. `0002-build-config.sub.patch` — 接受 `ohos` OS 与 `linux-ohos` kernel-OS 组合（含补上 `scripts/patch-autotools-ohos.pl` 第 2.3 步因顺序依赖误判 skip 的 kernel 白名单）
3. `0003-configure.patch` — 去掉 configure/config.status 临时目录的 `umask 077`（本机文件系统上 `mktemp -d` 的 2700 目录属主亦不可写）
4. `0004-configure.ac.patch` — libcurl 仅由 pkg-config 发现时也置 `have_libcurl`，恢复上游默认 curl WWW 后端
5. `0005-src-raptor_libxml.c.patch` — `xmlEntity.checked` 守卫补上界 `< 21100`（libxml2 2.11.0 移除该私有字段，同上游/发行版既定修复）

**已知限制**：
1. 上游 CMake 构建路径未注册任何测试，本配方只提供 autotools 构建；CMake 变体需另行补齐测试与验证。
2. 静态 `libraptor2.a` 内含 ICU 的 C++ 符号，消费者须同时链接 libc++（配方已在 `package_info()` 声明 `c++` 系统库）。
3. 包内 `raptor2.pc` 的 `Libs.private` 含 Conan 缓存绝对路径（上游 `raptor2.pc.in` 直接展开 `@RAPTOR_LDFLAGS@` 所致，本仓其它 autotools 配方同形态）；Conan 消费者走 CMakeDeps/PkgConfigDeps 不受影响。
4. 上游 `make check` 非并行安全（`tests/<suite>/` 内多个 `check-local` 循环目标共用结果文件名），配方以 `make check -j1` 串行执行。

**门禁状态**：W3 本地 CI 模拟通过并生成 `.ci-result.json`（`exit_code=0`，含日志 sha256）；W4 独立审计第二轮 `verdict=pass`（P0=0/P1=0/P2=0，2 条 P3 已修复），结果见 `reports/audit-result.json`。
