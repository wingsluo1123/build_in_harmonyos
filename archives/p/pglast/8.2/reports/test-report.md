# pglast 8.2 测试报告

上游官方sdist SHA256 e5d64c29281ecd9d001b5521b807be0e66375f356cbefda19c337c2253765496；原版9个测试文件未改。

|类别|总数|通过|跳过|预期失败|失败|
|---|---:|---:|---:|---:|---:|
|上游pytest|2420|2405|14|1|0|
|安装制品消费者|8|8|0|0|0|
|独立HarmonyOS机制|1|1|0|0|0|

上游普通通过率99.38%；适配后总数2429。14项为原版ty守卫跳过，test_issue157为原版预期失败；不伪报全数普通通过。平台测试验证未签名可写、签名加载后EPERM且SHA不变、同目录签名新inode替换后新进程实际SQL解析成功。完整计数、源文件SHA和原始日志SHA见native-validation-summary.json与formal-w3-summary.json。

## 2026-10-17 正式运行终态（覆盖上文启动前检查点）

唯一运行 pglast-8.2-review-20261017-w3-01，绑定软件提交96eaf3423b65241aecbc7cfdb2a42018c6b1cda4、框架main ad0c1a73eaeeb0807aebf150606a75a9ee950bd0。官方 W3 的 setup.sh 和 build_and_test.sh 均退出0，原始 .ci-result.json 的日志SHA已逐字节核验。强制源码重建后上游2405通过/14跳过/1预期失败，消费者8/8，独立平台机制1/1；不累计两次运行。

完整Finish仍为部分完成：全仓知识完整性检查发现主分支既有空字段（step5b）；冻结输入缺test-report.md（step8，本次补充真实报告）；Finish将conandata.yml去掉空行，控制器严格字节后检因此返回1，非空白内容完全一致。原始失败状态、WAL、释放记录及日志不改写，见formal-w3-summary.json。不能将W3子步骤退出0等同完整Finish通过或当前HEAD远端CI通过。独立控制器确认子进程已等待结束并释放资源；未重放本次运行。

native-validation-summary.json 中 verifier_input_files 明确属于独立Verifier02生产者时点；MANIFEST报告引用调整前的历史SHA保留。正式冻结与当前MANIFEST的SHA另列于formal-w3-summary.json，避免将历史时点哈希误当当前输入。
