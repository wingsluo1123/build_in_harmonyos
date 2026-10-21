# twodict 1.2 适配记录

## 固定来源与范围

原始 PyPI sdist 为 7036B，SHA256 `20dbdfa7f14a285454d34bba1e7714aad15a376ddfd0a1c0a3c24a14763bdb45`。源码只含一个运行模块和标准库依赖；许可证随包保留。直接复制单模块是包安装方式，不宣称 distutils 在 Python 3.12 构建成功。

## 源码修改清单

1. twodict.py：三类视图由 collections 旧别名迁移到 collections.abc。双向存储算法不变。
2. test_twodict.py：原 TestSetItem.tearDownForTestCases 的观测表达式由 super(...).copy() 改为 dict(dict.items(...))，保留所有原 expected_dict 和 assertEqual。公开映射只枚举正向条目，底层 dict 同时保存正反条目；调用父类 copy 仍可能经公开 keys 合并，不能把它当裸存储观察器。
3. 同一原测试 runner 把 TestResult.wasSuccessful() 传递到进程状态；保留 all_tests_suite() 入口及嵌套测试类，保留六个原 Python2-only 跳过。

## 已有主机结果（复用）

2026-10-13 Windows AMD64 / CPython 3.12.14：原始源码因 collections.KeysView 无法导入；仅 ABC 修复后完整套件发现 71、失败 16、原跳过 6，而原 runner 返回 0。补退出码后相同失败返回 1。更正存储观察表达式后发现 71、通过 65、原跳过 6、失败 0、rc0。本线程新增主机执行为 0。研究探针写出的测试文件使用 CRLF；候选保持上游 LF，测试文本无其他差异。

## 目标验证与未完成项

2026-10-13 H1-001 原始回收绑定候选 `73cd566b319e01ce8cdfc91f7048b1ff1a65688d`。OHOS6/armv8、Conan 2.29.1、真实 Python3.12.9 包运行原套件：发现71，执行通过65，六个原Python2跳过，失败0；安装模块消费者1流程/9断言通过。官方setup.sh和build_and_test.sh完成，W3日志及真实生成的.ci-result.json均记录exit_code=0。日志确认同对象public_items和parent_copy各含正向2项，raw_items包含正反4项，目标机制成立。详见 reports/test-report.md 和 reports/h1-001-w3-local-ci.log；本次没有重跑已完成的目标软件测试。

整体finish仍rc1，当前状态: failed。G1要求export_sources入口，原exports_sources属性虽然被真实Conan构建接受，却不满足官方G1；本次改为export_sources()调用export_conandata_patches，仅按相同conandata导出原两补丁，build/消费/源补丁不变。patches_applied补真实两文件，knowledge_gained改为实际草稿knowledge_ref。G0通过两补丁应用后默认调用不存在的./configure返回127；当前官方clean_verify只支持configure/make路径，不能给纯Python软件伪造configure或把该失败改写为通过。finish的gen_summary抛出str.append错误，本软件两份实际manifest在同一官方摘要解析器下均可解析，根因尚未定位；保留HOLD，待原H1用原现场取得准确异常栈。W5还报告官方原库E219/E253/E305空字段，不修改他人知识文件。

发布前仍缺失败收口的准确解除、独立W4、完整AtomCode、申请Issue/PR、面板关联、当前head官方CI与有效提审回读。平台任务#11383的lang=cpp与真实纯Python来源不一致；本次raw未提供有效语言预检回执，不伪作资格通过。

## 发现与知识

- ✅ 已形成实际配对草稿 knowledge_ref: E549-draft-34CB；目标运行确认公开映射与底层双向存储的观察边界，未正式索引或官方接受。

### 对话 #1

二级将H1-001的真实失败归档交回原作者，要求直接读原始错误、必要候选缺口做最小修正、不发布或占窗。作者核对归档SHA256、准确候选与原始执行日志，复用目标原套件/消费者/W3成功证据，修正G1入口和本库归档字段；框架适用性、全局摘要异常和语言资格保留准确缺口。
