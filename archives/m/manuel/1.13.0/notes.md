# 候选记录

- 账号 gcw_tlRDjnsx；task 8680；平台分支 feat/manuel-1.13.0。平台语言 cpp、
  实际包 Python 的差异保留，发布资格需按现行正常入口回读。
- 缺陷与两个正常完整结束行对照复用 2026-10-13 原 host 探针；没有重跑未变原探针。
- 第一次仅修比较边界时，完整原 suite 在加载 `index.txt` 的代码块时触发
  IndentationError，原 suite 没有完成执行。失败原件保全，不计通过。
- 根因补全：结束匹配自身含换行时，结束位置已经是下一行起点；
  扫描修正后若无该保护，会把下一行吞入原代码块。最终补丁保留该既有边界。
- 原 `break_up_region()` 行数断言完整保留，新增回归另查字符内容一致；
  这是普通跨平台核心缺陷，不标为 OHOS 专属，不扩展格式框架。
- Windows 源码/纯 wheel 验证通过；本机没有 Conan 模块，未声称本机 conan create。
  原二级经唯一H1取得002目标打包/消费者通过，详见下节。
- 原源码 `testcase.py` 的非法转义 SyntaxWarning，以及 setuptools 对原
  tests_require/test_suite 配置的警告保留，未为消除警告改上游测试或配置。
- zope.testing tests/docs extras不是原manuel suite必需依赖；只使用包自身的
  renormalizing 与 module。setuptools真实metadata运行依赖保留。
- H1-001 finish 自然 rc1，原候选13件及核心摘要吻合。Conan export_sources 引用的旧
  补丁名被官方 refresh-patch 备份移走；W3 L0 因 application 声明触发 CLI 清单要求。
  H1-002 仅同步生成补丁名与 strip=1、改为无可执行入口的 unknown 包类型；源码不变。
  G0 对纯 Python 运行 ./configure 的 rc127 保留为遗留工具冲突，不制造 configure/marker。
  目标软件测试、打包及消费者在001均未开始；002独立结果在下节，旧调用不改成PASS。

## H1-002 actual target result (2026-10-14)

OHOS6.0 armv8 / Clang15 libc++ cppstd17 Release / published Python3.12.9.
Conan2.29.1 create/build/package/test_package and original suite passed: 63/63
unittest groups, 273/273 original doctest examples, 6/6 added boundary regressions,
and one delivered-package extraction/claim/reassembly consumer with 5 assertions.
The actual consumer imports Manuel from the new Conan package. Package core SHA256
remains dc3ae247600365d4f3a1a5444a5d9697feb9f78670bdd94271153c7c38fb9ca3.
Original corpus, tests and doc1/2/3.ex are byte-identical in that package.

Actual local package: `manuel/1.13.0#34a5a794c5652c2f1f91305ae7246710:da39a3ee5e6b4b0d3255bfef95601890afd80709#fe7c7c66491dc64079a3c9046deaf2cc`. No manual upload/publication is claimed.
W3 G0 knowledge integrity, KC, JC, L0/L1/L4/L5 passed (JC_ERRORS=0); L2 skipped
because this pure Python package has no bin directory. This W3 G0 differs from the
legacy H1-001 clean-build ./configure check, whose rc127 and finish rc1 remain FAIL.
H1-001 patch export and CLI metadata failures also remain in their original record.
The three official W3 source pre-download warnings remain; the recipe used the
fixed hash-checked source and pure wheels supplied by the original H1.

This publication preparation changes only result documentation/manifest metadata.
Recipe, conandata, patch, observer, regressions, test_package and original corpus
are unchanged from tested002. No software or W3 rerun. Independent W4, actual
AtomCode full-range review, Issue/PR association, official PR CI and effective
submission remain pending; local W3 success does not establish those states.
