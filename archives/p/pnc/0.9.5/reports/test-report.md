# pnc 0.9.5 测试报告

> **项目**: pnc（libphonenumber 命令行封装）
> **测试日期**: 2026-10-15
> **测试环境**: HarmonyOS PC aarch64（OS 6.0 / clang 15 / Conan 2.29.1）
> **测试类型**: 上游官方测试套件 + 消费者端到端验证

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 24 | 100% |
| 通过 (PASS) | 24 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

口径说明：

- 上游 `tests.sh` 断言 11 项（CTest 注册为 `tests_sh`，在 `build()` 内由
  `cmake.test()` 真跑，CI 与本地同源），1/1 test passed。
- 消费者 `test_package/test.sh` 断言 12 项，只用安装后的产物。
- 鸿蒙特有测试 1 项：真机端到端消费用例 `test_package/consumer-e2e.sh`
  （通讯录导出原文 → 规范化联系人表，五步串联，产物与期望文件比对）。
- 三项合计 24 项，与 `manifest.yaml:test_results` 一致。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** —— 上游测试全绿，消费者端到端全绿。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| GNU AWK 扩展（`gawkpn.so`）未纳入本包 | 该扩展的 `pn_info`（ICU 地理编码）路径在进程退出阶段随机崩溃 | 🔴 未发布 |

### 2.3 可用功能清单

```
✅ pnc valid    号码校验（含各国上下文、退出码语义）
✅ pnc info     号码信息 + 离线地理编码归属地
✅ pnc format   e164 / int / nat / teluri 四种输出格式
✅ pnc find     从自然语言文本中抽取号码
✅ pnc dialout  生成国际拨号串
❌ gawkpn.so    GNU AWK 扩展：未随本包构建（原因见下）
```

### 2.4 已知限制

1. **GNU AWK 扩展未纳入本包**。上游同一份源码还构建 `gawkext/gawkpn.so`，实测在
   OHOS PC 上于进程退出阶段随机以 SIGTRAP/SIGABRT 终止（输出已完整产出），
   触发条件是走 ICU 地理编码的 `pn_info`：该组合每项 40 次运行有 10–17 次失败
   （上游原实现 17/40，成功率 57.5%–75%）；同环境 gawk 自带的 `filefuncs` 扩展
   40/40 正常，同一批代码在 CLI 里 180/180 正常。已排除 `make_const_string`+`free`、
   NUL 结尾、全局对象析构、DSO 卸载等方向，取证过程见 `notes.md`。该扩展留作
   `pnc-gawk` 任务跟进。
2. 本包为 `package_type = "application"`，不导出可链接的库。

---

## 三、测试环境与命令

```sh
# 上游测试（配方 build() 内）
conan create archives/p/pnc/0.9.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#   → ctest: 1/1 tests_sh Passed

# 消费者测试（conan create 自动触发 test_package）
#   → 步骤 1: test.sh           结果: 12 passed, 0 failed / ALL PASSED
#   → 步骤 2: consumer-e2e.sh   结果: 端到端消费用例: PASSED（产物与期望逐行一致）
```

## 四、真机端到端消费用例

用例脚本 `test_package/consumer-e2e.sh` 由 `test_package/conanfile.py` 在
`conan create` 中调用（CI 与本地同源），全程只用安装后的 `bin/pnc`：

**场景**：一份「通讯录导出原文」（法/英/德混合自由文本 + 无效噪声）
→ 规范化联系人表。判据是**生成的联系人表本身**，不是孤立断言。

| 步骤 | 命令 | 作用 |
|:----:|------|------|
| 1 | `pnc find -c FR <原文>` | 从混合语言原文抽出 5 个号码（本国格式 + 国际格式），排序去重 |
| 2 | `pnc valid <号码>` | 逐号校验（退出码 0），并确认噪声 `poste 1234` 被拒（非 0） |
| 3 | `pnc info <号码>` | 取归属国家码 / 号码类型 / 离线地理编码地点 |
| 4 | `pnc format -f nat <号码>` | 生成法国本地书写格式 |
| 5 | `pnc dialout -c US <号码>` | 生成从美国拨出的国际拨号串 |

产物 `contacts.sheet.tsv`（5 行）与黄金文件 `test_package/data/expected.sheet.tsv`
逐行比对：

```
e164            cc  type                   location          nat_fr          dial_from_us
+12025550110    US  fixed line or mobile   Washington D.C.   (202) 555-0110  1 (202) 555-0110
+33123456789    FR  fixed line             France            01 23 45 67 89  011 33 1 23 45 67 89
+33155487002    FR  fixed line             France            01 55 48 70 02  011 33 1 55 48 70 02
+442079460958   GB  fixed line             London            020 7946 0958   011 44 20 7946 0958
+49301234567    DE  fixed line             Berlin            030 1234567     011 49 30 1234567
```

用例在本机（HarmonyOS PC aarch64 / OS 6.0）与 CI worker 上均以退出码 0 通过。

## 五、复现命令（AWK 扩展缺陷）

```sh
# 对照组：gawk 自带扩展（同环境）
AWKLIBPATH=<gawk-pkg>/lib/gawk gawk -e 'BEGIN{print "x"; stat("/etc", s)}'   # 40/40 正常

# 被测：gawkpn 扩展
AWKLIBPATH=<pnc-pkg>/lib/gawk gawk -f L2.awk    # L2.awk: pn_info + 读 i["location"]
#   → 40 次中 17 次 rc=133/134（输出已完整产出）
```
