# pglast 8.2：2026-10-17 当前输入验证摘要

本轮修复 PR !15502 的 rule12：新增独立 HarmonyOS 签名 ELF 机制测试，保留原有8项消费者，不将普通消费者重分类为平台测试。

## 当前实测

- 新鲜隔离目标 host/build 图及 `--build=never` 安装成功；4项根依赖为 Python3.12.9、setuptools84.0.0、Cython3.3.0、pytest9.1.1，完整节点与哈希见 w0-dependencies-summary.json。
- 使用当前 main ad0c1a73eaeeb0807aebf150606a75a9ee950bd0 原始官方 Verifier，第二轮退出0。首轮G1因旧配方缺标准patch钩子退出1，日志保留；已添加真实 export_conandata_patches/apply_conandata_patches，无上游补丁。
- 当前原生上游2420项：2405通过、14 ty跳过、1原版 test_issue157预期失败、0失败，普通通过率99.38%。9个原版测试文件与官方sdist逐字节一致，未改断言/参数化/守卫。逐文件计数和14跳过/1预期失败明细见 native-validation-summary.json。
- 当前安装消费者8/8；独立平台机制测试1/1。适配后总数2429=77单元+2323集成+28类型检查其他+1平台机制，不累计重复运行或诊断断言。
- 平台测试是真实目标原生：无签名副本写入成功；签名并加载后同一写入返回EPERM且SHA不变；新签名inode原子替换后新解释器从准确私有路径解析不同SQL值成功。只写临时副本，不改安装缓存。
- 当前Conan引用：`pglast/8.2@ohpcd/stable#c2235bb6e21c09685bb1a2a8828c4cfe:6b129b068851896169fae42d399fa922d239ce8a`。目标identity、源码SHA、输入SHA与原始生产者/JUnit SHA均在结构化摘要中；完整原始材料保留任务交付目录，不是公开下载链接。

## 保留的边界

ty官方Linux/musl AArch64程序不兼容的14项原版跳过保留；先前Windows同8.2官方wheel的28/28仅为补充历史证据，不等于本轮真机ty成功，不加总。coverage仪表关闭，不宣称目标覆盖率。

官方Verifier虽然返回0，G0风险预查询因unknown跳过，G4不能解析package ID，L2/L4/L5因缺cache路径跳过，不能据其PASS标签冒充实际执行。完整正式Finish/W3本轮尚未启动；旧2026-10-13回执不继承到本轮输入。远端CI、Review、实际提审、合并、发布分别核验。

## 大体量材料与审查

原PR的AI检视因13文件/11200行跳过。原始Conan运行图及2420项JUnit保留本地并列SHA，提交结构化节点、逐模块统计、失败/跳过明细和源文件哈希，避免将大体量运行图当成需逐行审查的源码。没有删除任何上游测试。

知识查重已在当前main graph/drafts/doc/operations复核：E016最高0.23，E1761=0.18、E601=0.17，工具建议create。原CPU配置×编译器宏×保留函数闭包候选保持；新增签名平台测试只作为真实交付证据，不单独申请额外创新分。路径B正式资格、定号及积分待官方。

## 结束

当前本地原生状态built；完整本轮W3/当前HEAD远端CI及审查闭环尚未验收，不能报告完整交付成功。

## 2026-10-17 正式运行终态（覆盖上文启动前检查点）

唯一运行 pglast-8.2-review-20261017-w3-01，绑定软件提交96eaf3423b65241aecbc7cfdb2a42018c6b1cda4、框架main ad0c1a73eaeeb0807aebf150606a75a9ee950bd0。官方 W3 的 setup.sh 和 build_and_test.sh 均退出0，原始 .ci-result.json 的日志SHA已逐字节核验。强制源码重建后上游2405通过/14跳过/1预期失败，消费者8/8，独立平台机制1/1；不累计两次运行。

完整Finish仍为部分完成：全仓知识完整性检查发现主分支既有空字段（step5b）；冻结输入缺test-report.md（step8，本次补充真实报告）；Finish将conandata.yml去掉空行，控制器严格字节后检因此返回1，非空白内容完全一致。原始失败状态、WAL、释放记录及日志不改写，见formal-w3-summary.json。不能将W3子步骤退出0等同完整Finish通过或当前HEAD远端CI通过。独立控制器确认子进程已等待结束并释放资源；未重放本次运行。

native-validation-summary.json 中 verifier_input_files 明确属于独立Verifier02生产者时点；MANIFEST报告引用调整前的历史SHA保留。正式冻结与当前MANIFEST的SHA另列于formal-w3-summary.json，避免将历史时点哈希误当当前输入。

### 对话 #1（2026-10-17）

用户要求解决PR !15502最新审查意见并按模板填写。依据原讨论rule12新增独立签名机制测试，rule7继续绑定当前提交远端CI。状态：built；完整Finish部分完成，未提审、未合并、未发布。
