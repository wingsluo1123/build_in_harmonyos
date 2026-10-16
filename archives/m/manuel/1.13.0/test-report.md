# 测试结果与统计口径

Windows Python3.12.14 和 H1-002 OHOS Python3.12.9 均有真实通过原件。
下表为两端同口径结果；H1-001 的前构建失败仍单列保留。

| 验证项 | host与H1-002目标结果 | 单位 |
|---|---|---|
| 完整原 `manuel.tests.test_suite` | 63/63 | unittest 执行分组 |
| 原语料 doctest | 273/273 | 原解析并执行的 doctest Example |
| 原代码块 | 32 | 原suite含的 CodeBlock；随上面63组执行，不重复加总 |
| 新增边界回归 | 6/6 | unittest case |
| wheel包消费者 | 1/1 | 完整流程，5断言，不按断言数计5个消费者 |

原 doctest 分母：index114、table22、README87、bugs33、capture14、tests.py3，合计273。
MyST语料使用4个代码块，包含在32个原代码块内，没有原doctest提示符。
源测试/文档/三个doc*.ex原件与修后源码、实际wheel中的字节全部一致。

观察原 suite 时还记录了6个由代码块内部生成的 `<memory>` doctest 例子和
57个嵌套演示例子。后者有12个预期失败示范，原测试的外层断言全部通过；
这些执行不加到原语料273分母，也不改成软件失败或虚构新增用例。
原终端 `Ran 63 tests / OK` 与这个 doctest 口径是不同单位。

首次比较符单点修法在原suite构造阶段FAIL（IndentationError），分母未执行，
不写0/0=100%。H1-001：Conan create FAIL（export_sources 引用失效的旧补丁名），
W3 L0 FAIL（误声明 application 导致 commands.json 要求），L1/L2/L4/L5 均 SKIP。
原 suite/回归/包消费者均 NOT_RUN；G0 的 ./configure rc127 为另列的遗留工具冲突。
H1-002 只改补丁文件引用/剥离层级与真实包类型，修后核心及测试输入完全不变，
复用以上本机结果；H1-002 目标实际结果见下节，不覆盖001原失败。

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
