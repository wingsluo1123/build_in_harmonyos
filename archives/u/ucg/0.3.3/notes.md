# ucg 0.3.3：当前验证边界

## 2026-10-12 最终候选

完整 61 个 Autotest 注册组及两个原 TEST_F 均执行：59 Autotest PASS + 原 XFAIL
28/30、GoogleTest 2/2；合计 61 普通通过 + 2 原预期失败，无 SKIP/FAIL/XPASS。
XFAIL 实际日志同时校验精确源行、匹配数 diff 与空 stderr，不接受无关失败。
新增安装消费者 5/5，官方 L1e 移走 bin/ 后能证明反向依赖。

Boost 1.58、Linux 4.8 源码搜索树和 OpenSubtitles2016 全量数据已按同一 SHA
验证并用于原十次迭代；无缩小 fixture。Linux 未宣称构建成内核；benchmark diff
是原统计，并非逐字节一致断言。原 GoogleTest 空占位的覆盖边界照实披露。

可选 GNU grep 的手写 atlocal.in 检查拒绝 `is not GNU grep` 否定 banner，
保留必需系统 grep、所有组和数据。新知识 E11425-draft-2501 配对草稿说明
版本文本品牌子串不等于肯定身份，以及可选/必需角色边界和验证方法。

正式 r14 finish 的 Conan verify、W3_local_ci exit0；全部 12 phase 及释放 PASS。
官方 `.ci-result.json` 原生生成，W3 log SHA256
97b5b8efa505489bdd0a80e3d2535809aed1a9ddebb4b8015ae955751d761e77。
Aggregate finish 原 RC1 仅后置 step5b/step8，不伪报全流程 PASS；当前知识完整性
和 Pre-PR 两阶段合同单独闭环。旧 r13 controller 读错消费者标记，整体 FAIL
保持不变，已释放；r14 独立完整执行，未拼接旧 PASS。未宣称 worker CI/Review/发布通过。

## 历史定向与失败记录（不用于替代最终全量验证）

CLI 歧义选项测试原来失败于辅助 grep 的 GNU 长选项，不是 ucg 返回码。
保持原始断言和正则，用手写 AT 的等价 `-i` 调用；Autom4te 2.72 重建完整
testsuite 后，原生定向组 12/13 通过。导出源及生成脚本，避免要求目标机重新
运行未经验证的生成器或直接改分发的生成物。

两项原始 GTest 在 corpus 基准之前独立执行，XML 验证 2 项、零失败/错误/禁用。
包含上游现有的空 `SomeOtherTest`，不把它包装为新增功能覆盖。

2026-10-11 r10 只执行两项 Autotest 和两项 GTest，不能代表上游 63/63。
生产配方仍拒绝局部测试摘要；消费者和包创建没有通过。

2026-10-12 用户要求补齐全量后提交。完整官方 Boost1.58、Linux4.8 源码和
OpenSubtitles2016 英文数据均已取得；字幕全流 gzip 校验通过（解压9968530111字节）。
配方下载并校验真实语料，保持原10次基准迭代和全部61组；Linux是搜索用源码树，
不声明内核已构建。上游 performance_tests.at 使用 Git 比较输出，因此声明已发布
Git2.45.2工具依赖。两项 GTest 仍保持原用例。

原始28/30明确以 AT_XFAIL_IF(true) 记录 glob 优先级的已知缺陷，不能把
“All 61 tests behaved as expected”误判失败，也不能只接受任意XFAIL标签：
逐ID核对59 PASS+2原始XFAIL，限制原5→0/0→5差异和空stderr，拒绝崩溃、
错原因、SKIP、FAIL和XPASS。该口径不等于修复了上游这两项语义缺陷。
10.62.201.39:2222连接已恢复；r12已跑到完整大语料基准，但仍不能声明全量或消费者通过。

原Autotest成功汇总不附XFAIL明细，必须读取原testsuite.dir/28与30的真实组日志；
仅对汇总找两项expected failure会误拒正常结束。已修复调用方，旧冻结r12不重标。

本机真机程序版本/计时报告还证明GNU角色误探：Toybox的首行写明
“is not GNU grep9.0”，上游子串测试仍把它当作GNU grep，再重复登记同一个
/system/bin/grep。下一版在手写atlocal.in模板检查首行GNU品牌括号，保留真正GNU，
清除这个非GNU额外角色；mandatory systemgrep、63个注册用例、语料和每组迭代数均不减。
这只纠正工具身份，不把品牌文字当作完整功能证明。Benchmark中diff统计未被上游当作
失败断言，不能把其成功报为不同工具的逐字节等价（字幕基准原grep过滤不匹配扩展名，
ucg实测1543行而grep0行，差异如实保留）。
