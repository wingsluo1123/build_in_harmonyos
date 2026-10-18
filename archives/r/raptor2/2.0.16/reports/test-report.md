# raptor2 2.0.16 测试报告

> **项目**: raptor2（Raptor RDF Syntax Library）2.0.16
> **测试日期**: 2026-10-16
> **测试环境**: HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64（原生构建，build == host），clang 15.0.4，Conan 2.29.1，profile `ohos-aarch64`
> **测试类型**: 上游官方测试套件 + 鸿蒙消费者端到端用例

---

## 一、测试摘要

### 1.1 上游测试套件（`make check`，由配方的 `conan create` 执行）

| 套件 | 统计单位 | 总数 | PASS | FAIL | SKIP | 说明 |
|:----:|:----:|:----:|:----:|:----:|:----:|------|
| `src/` | automake TESTS 程序 | 19 | 19 | 0 | 0 | 单元/组件测试程序 |
| `tests/*/` | 数据驱动检查项 | 1233 | 1205 | 28 | 0 | 13 个子套件（rdfxml、turtle、turtle-2013、ntriples、ntriples-2013、nquads-2013、trig、mkr、grddl、rdfa、rdfa11、json、feeds） |
| **合计** | — | **1252** | **1224** | **28** | **0** | `make check` 退出码 **0** |

- 28 项 FAIL 全部落在 `tests/rdfa`（4 项）与 `tests/rdfa11`（24 项），与上游 `Makefile.am` 中的 `EXPECTED_FAILURES` 清单**逐字一致**，harness 输出 `Ignoring expected failures` 并令 `result=0`。属上游声明的预期失败（XFAIL 等价物），非适配引入。
- `src/test-suite.log`：`# TOTAL: 19 / # PASS: 19 / # FAIL: 0`。
- 解析器/序列化器全量启用（10 个解析器、11 个序列化器）：RDF/XML、N-Triples、Turtle、TriG、N-Quads、RSS tag soup、RDFa、RDF/JSON、GRDDL、guess；WWW 后端为 libcurl；NFC 校验库为 ICU UC 78.3。配方内 `_assert_full_feature_set()` 断言 19 个特性宏，任一缺失即构建失败。

### 1.2 鸿蒙消费者端到端用例（`test_package`，在目标机实际运行）

| 用例 ID | 场景 | 输入 | 被测对象 | 判定 | 结果 |
|:----:|------|------|----------|------|:----:|
| R12-01 | 库 API 端到端：同一数据集以 Turtle 与 RDF/XML 两种语法解析，各自序列化为 N-Triples，断言两种语法产出同一组语句 | `test_package/data/sample.ttl`、`sample.rdf` | `raptor2/2.0.16` 安装后的 `libraptor2`（`raptor_new_parser` / `raptor_parser_parse_file` / `raptor_new_serializer` / `raptor_serializer_start_to_string`） | 两种语法各 3 条语句；排序后逐行相等；且 3 条预期语句逐字出现 | **PASS** |
| R12-02 | CLI 端到端：执行包内 `rapper` 把 RDF/XML 转成 N-Triples，断言实际业务输出 | `test_package/data/sample.rdf` | 包内 `bin/rapper` | 输出的 N-Triples 含全部 3 条预期语句 | **PASS** |

实测输出（`conan create` 日志，`raptor2/2.0.16 (test package)` 段）：

```
parsed .../data/sample.ttl (3 triples) and .../data/sample.rdf (3 triples)
all 3 expected statements present (Turtle == RDF/XML)
RESULT: PASS — raptor2 parsed Turtle and RDF/XML and produced identical N-Triples
raptor2/2.0.16 (test package): rapper CLI produced all 3 expected statements
```

预期语句（业务输出，逐字断言）：

```
<http://example.org/alice> <http://example.org/knows> <http://example.org/bob> .
<http://example.org/alice> <http://example.org/name> "Alice" .
<http://example.org/bob> <http://example.org/name> "Bob" .
```

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游 `make check` 退出码 0；`src/` 19/19 通过；`tests/` 语料 1233 项中 1205 项通过，其余 28 项为上游声明的预期失败；2 个鸿蒙消费者端到端用例在目标机实际 PASS。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 | 处置 |
|----------|----------|:--------:|------|
| 上游预期失败（rdfa 4 项、rdfa11 24 项） | `tests/rdfa`、`tests/rdfa11` 的 RDFa 1.0/1.1 边界用例 | 🟢 无 | 上游 `EXPECTED_FAILURES` 显式声明；不属于适配缺陷，未修改、未删除任何用例 |
| 上游 `make check` 非并行安全 | `tests/<suite>/` 内多个 `check-local` 循环目标共用结果文件名 | 🟡 中 | 配方以 `make check -j1` 串行执行（并行会互相覆盖 `*.res`） |
| 包内 `raptor2.pc` 的 `Libs.private` 含 Conan 缓存绝对路径 | 仅影响使用该 .pc 做静态链接的非 Conan 消费者 | 🟢 低 | 上游 `raptor2.pc.in` 直接展开 `@RAPTOR_LDFLAGS@` 所致；本仓其他 autotools 配方（含 curl）同样形态；Conan 消费者走 CMakeDeps/PkgConfigDeps 不受影响 |

### 2.3 可用功能清单

```
✅ RDF/XML、N-Triples、Turtle、TriG、N-Quads、RSS、RDFa、RDF/JSON、GRDDL 解析
✅ RDF/XML(+abbrev)、Turtle、mKR、N-Triples、N-Quads、RSS 1.0、Atom 1.0、JSON、DOT、HTML 序列化
✅ HTTP/HTTPS 抓取（libcurl WWW 后端）
✅ Unicode NFC 校验（ICU UC 78.3）
✅ rapper 命令行工具
```

### 2.4 已知限制

1. 上游 CMake 构建路径未注册任何测试，本配方只提供 autotools 构建；CMake 变体需另行补齐测试与验证。
2. 静态 `libraptor2.a` 内含 ICU 的 C++ 符号，消费者必须同时链接 libc++（配方已在 `package_info()` 声明 `c++` 系统库）。
3. `Libs.private` 不可重定位（见 2.2）。

---

## 三、复现方式

```bash
conan create archives/r/raptor2/2.0.16 \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -r=ohpcd
```

该命令从官方 tarball（sha256 `089db78d7ac982354bdbf39d973baf09581e6904ac4c92a98c5caadb3de44680`）开始，应用 `patches/` 下 5 个补丁，执行完整 `make check` 与上述 2 个消费者用例。实测退出码 0。
