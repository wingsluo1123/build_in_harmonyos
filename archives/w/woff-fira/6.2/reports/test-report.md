# 测试报告

> **项目**: woff-fira 6.2
> **测试日期**: 2026-10-15
> **测试环境**: Conan 目标 profile `OHOS 6.0 / armv8`；HarmonyOS PC 真机 `OpenHarmony 6.1.0.115`、aarch64、ArkWeb 6.1.0.115
> **测试类型**: Conan 消费者测试 + HarmonyOS PC 浏览器手动功能测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

上游发行包没有可运行的自动化测试，因此上游测试数为 0，不计入上述两项适配验证。

## 二、测试结论

### 2.1 总体评价

✅ Conan 包中的六种 WOFF 字体均通过包内容校验，并由 HarmonyOS PC 浏览器实际加载和绘制。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 未发现适配问题 | 本次测试覆盖范围 | 🟢 |

### 2.3 可用功能清单

```
✅ Conan 安装目录包含六个预期 WOFF 文件及 OFL-1.1 许可证。
✅ ArkWeb FontFace API 加载六种字体成功。
✅ Canvas 绘制 Fira Code 字形成功，且结果与系统 monospace 存在可测像素差异。
```

### 2.4 已知限制

1. WOFF 用于 WebView/浏览器字体加载；此包不会将字体注册为 HarmonyOS 全局原生字体。
2. 真机系统实际报告为 OpenHarmony 6.1.0.115；Conan 的 aarch64 目标 profile 为 OHOS 6.0。此次真机绘制测试不代表在物理 6.0 设备上运行。
3. 真机 `finish` 全流程为 partial：Conan、W3 aarch64 本地 CI、包级知识关联检查和 submit 就绪预检通过；仓库级 W5 因既有知识图谱字段问题未通过，详情见第六节。

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| Conan `test_package` | 校验六文件集合、WOFF 头字段、长度、SHA-256 和许可证，共 45 项检查 | ✅ PASS |
| HarmonyOS PC WebView 字体测试 | 真机浏览器加载六种字体并绘制到 Canvas，检查实际像素变化 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无。上游 release zip 不包含测试目录、注册测试套件或构建系统。

## 四、关键问题分析

本次测试未发现阻塞问题。

## 五、测试环境

```text
Conan profile: os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15
Package type: data-only; no native compiler invocation is required
Device: HUAWEI MateBook Pro, HarmonyOS product version HAD-W24 6.1.0.117
Device OS: OpenHarmony-6.1.0.115; HarmonyOS kernel 1.12.0; aarch64
Browser: ArkWeb 6.1.0.115 / HuaweiBrowser 6.1.1.351
Harmony test: all six FontFace loads succeeded; changed pixel counts were
Light 11930, Regular 12692, Medium 13450, SemiBold 14229, Bold 14700, VF 12693.
```

## 六、真机 finish 门禁结果

本次在 HarmonyOS 真机 SSH 工作区运行了完整 `finish woff-fira 6.2 built`。Conan 配方验证与消费者测试、OHOS 6.0/aarch64 W3 本地 CI、包级知识关联检查（2 条均已引用）和 submit 就绪预检通过。整体流程因仓库级 W5 返回 partial：E219/E253 在上游基线中缺少 `root_cause`；E305 的 `root_cause` 和 `rec_approach` 使用带正文的 YAML `|` 多行块，检查器只取字段首行后误判为空。该问题不在本包范围内。

G0/归档终检报告缺少源 tarball、release tar.gz 和 debug tar.gz；本包消费上游 zip 且为纯数据包，不产出这些构建归档。finish 的 SUMMARY 生成器还报告 `'str' object has no attribute 'append'`，但未阻断 Conan、W3 和 submit 就绪检查。

*报告生成时间: 2026-10-15*
