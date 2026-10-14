# 测试报告 — xmlto 0.0.29

**项目**: xmlto
**版本**: 0.0.29
**测试日期**: 2026-10-09
**测试环境**: HarmonyOS HongMeng Kernel aarch64 (clang 15.0.4 / OHOS 6.0)
**测试类型**: 上游官方测试套件 + test_package 消费者端到端用例

---

## 一、测试摘要

| 层级 | 命令 | 总数 | 通过 | 失败 | 跳过 | 日志 |
|:----:|------|:----:|:----:|:----:|:----:|------|
| 上游测试 | `bash xmlif/test/run-test` | 8 | 8 | 0 | 0 | `reports/upstream-test.log` |
| test_package（消费者端到端） | `sh test_package/consumer_test.sh <bindir>` | 3 组 | 3 | 0 | 0 | `reports/conan-create.log` §Testing the package |
| **合计** | | **11** | **11** | **0** | **0** | |

**通过率**: ✅ **100%**

---

## 二、上游测试（实际执行，逐用例）

**测试命令**

```bash
top_builddir=<layout> top_srcdir=<layout> bash xmlif/test/run-test   # 上游入口
```

被测二进制为**已打包**的 `xmlif`（OHOS aarch64 ELF），夹具为上游 `xmlif/test/test.xml`
与 `result-*` 期望文件。

| # | 用例名 | 命令 | 结果 |
|---|--------|------|------|
| 1 | no-condition | `xmlif < test.xml` | ✅ PASS |
| 2 | unrelated-condition | `xmlif unrelated=condition < test.xml` | ✅ PASS |
| 3 | html | `xmlif condition=html < test.xml` | ✅ PASS |
| 4 | pdf | `xmlif condition=pdf < test.xml` | ✅ PASS |
| 5 | ps | `xmlif condition=ps < test.xml` | ✅ PASS |
| 6 | foo | `xmlif condition=foo < test.xml` | ✅ PASS |
| 7 | baz | `xmlif condition=baz < test.xml` | ✅ PASS |
| 8 | bar | `xmlif condition=bar < test.xml` | ✅ PASS |

- 总数 8 / 通过 8 / 失败 0 / 跳过 0
- 判定方式：与上游 `result-<case>` 逐字节 `cmp`；`run-test` 整体退出码 = 0
- 原始日志：`reports/upstream-test.log`（含 `UPSTREAM_RUN_TEST_EXIT=0` 与逐用例明细）

> 说明：上游 `xmlto` 本体没有自动化测试入口（`make check` 无可执行目标）；
> xmlto 的官方测试即 `xmlif/test/run-test`，`test_package/MANIFEST.yml` 中已如实声明。

---

## 三、test_package 消费者端到端用例（HarmonyOS 专有非断言测试 + 业务闭环）

**测试命令**

```bash
sh test_package/consumer_test.sh <package>/bin
```

判定全部基于命令退出码（`self.run` / `cmp`），**不使用 Python assert**。

### A. HarmonyOS 专有非断言测试 —— 原生 ELF 与动态依赖闭包加载

| 步骤 | 检查内容 | 命令 | 结果 |
|------|----------|------|------|
| A1 | xmlif 是 ELF 且为 aarch64（OHOS 原生） | `readelf -h xmlif` | ✅ PASS |
| A2 | 动态依赖闭包存在且含 libc.so | `readelf -d xmlif` | ✅ PASS |
| A3 | 闭包在本机真实加载（原生执行 xmlif） | `xmlif </dev/null` | ✅ PASS |

实测证据：

```
xmlif: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
Dynamic section ... (NEEDED)  Shared library: [libc.so]
OK A: xmlif 原生 aarch64 ELF，DT_NEEDED 闭包（含 libc.so）在本机真实加载成功
```

### B. 端到端消费者用例（构造输入 → 真实执行业务 → 产出结果 → 校验内容）

| 用例 | 构造输入 | 真实执行 | 产出 | 校验 | 结果 |
|------|----------|----------|------|------|------|
| B1 | `doc.xml` + `style.xsl` | `xmlto -x style.xsl --skip-validation -o out html doc.xml` | `out/doc.proc` | 产物含 `<h1>HarmonyOS</h1>` | ✅ PASS |
| B2 | 上游 `xmlif/test/test.xml` | `xmlif < input.xml` / `xmlif condition=html < input.xml` | 两份输出 | 与上游 `result-no-condition` / `result-html` 逐字节 `cmp` | ✅ PASS |

实测证据：

```
OK B1: xmlto 真实转换产物内容校验通过
OK B2: xmlif 条件过滤两种输入均与上游期望逐字节一致
ALL CONSUMER TESTS PASSED
```

> B1 使用 xmlto 主工具完成一次真实 XML→HTML 转换（`-x` 指定样式表，`--skip-validation`
> 跳过 docbook 校验），校验产物内容；运行期依赖 `xsltproc`，环境未提供时会输出
> `SKIP B1` 并保留 A/B2 闭环（B2 为自包含闭环，无外部依赖）。

---

## 四、conan create 证据

- 命令：`conan create archives/x/xmlto/0.0.29 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build='xmlto/*' --user=ohpcd --channel=stable`
- 退出码：`0`
- 日志：`reports/conan-create.log`（206 行，含真实构建段）
  - `Building from source`（:74）→ `Bootstrapping autotools ... m4 bin=...`（:84）→ 三步自举 `RUN: PATH=... M4="<m4包>/bin/m4" sh -c 'perl .../.aclocal-real' / 'autoconf -o configure' / 'perl .../.automake-real'`（:85/:87/:89，输出重定向到独立日志）→ `sh "<src>/configure" ...`（:91）→ `clang ... -c xmlif.c`（:93）→ `Packaged 36 files`（:102）→ `Package ... created`（:105）
  - `Testing the package` → `RUN: sh ".../consumer_test.sh" ...` → `OK A`（:196）/ `OK B1`（:200）/ `OK B2`（:204）→ `ALL CONSUMER TESTS PASSED`（:205）

---

## 五、测试环境

```
xmlto/0.0.29
Compiler: clang 15.0.4 (OHOS)
Profile: ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8)
build_type=Release
```

---

*报告生成时间: 2026-10-09（2026-10-12 按 CI #85406 修复后配方重建证据日志后复核）*
