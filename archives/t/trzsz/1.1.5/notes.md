# trzsz 1.1.5 适配与验证记录

账号 orrkri，主活动任务 11309，分支 `feat/trzsz-1.1.5`。任务语言字段 cpp，固定真实上游为 Python；沿项目人工发布裁决披露差异，不修改任务标签，不套 AI Worker 终态上报释放任务。受支持入口若拒绝，保留真实拒绝。

## 固定来源和实际包

官方 commit `e433a8c326dddd1b7a9fe79f3f1b766f76fe9ca8`，完整源归档 SHA256 `4d9a4087fd69b07b5a0209843e79f1a7e4907ea985b8332d76bb1fcbe0ff1dd6`。三份真实 PyPI sdist 的 URL/摘要见 conandata.yml；模块与固定 commit 一致，8 条真实 symlink payload 保留。H1 从原 tar 解包，原测试链接没有改为 Windows 阅读副本。

同版 metapackage、libs、svr 的完整真实 egg-info、requires、entry_points 与 namespace 一起打包。libs 无第三方运行依赖，svr 依赖同版 libs；可选 iTerm2 extra 不属于默认范围。许可证为固定源码 LICENSE.md。

实际依赖闭包为 `python/3.12.9#d8eda770878152bea40b42db9f7024cd:6c7db42132821d241106bb3c9ac38ad21bf97eec#a71d1eefc7332dae9aba6862098bb2b2`，OHOS6/armv8/clang15/libc++/cpp17/Release。运行环境只按 dependency package_folder 作用域设置 PYTHONHOME；包消费者核 bin/python3、sys.prefix、3.12.9、实际本包 modules 与 OHOS termios。未改全局 Python、HOME 或认证。

## 补丁与受测输入

只修改 canonical `trzsz-libs/trzsz/libs/transfer.py` 两处：发送端在 `while step < size` 内读后、send_data 前拒绝空 bytes；接收端在同一条件内 decoded DATA 后、file.write 和 SUCC 前拒绝空 bytes。抛原 `TrzszError('Unexpected end of file', trace=False)` / `TrzszError('Received empty file data', trace=False)`，沿原 fail 协议传播。合法 SIZE=0、MD5 和 CLI rc 语义保持。

H1 实际 official refresh-patch 生成 `0001-trzsz-libs-trzsz-libs-transfer.py.patch`，SHA256 `2fe5709f5680428cfc7bcd12e2b58982450f5ddb6abfb06636a17f98e3938335`；真实 dry-run/apply 成功，包内 transfer.py SHA256 `1c3e5318de04c58446fcb0fa80dfcaa882b39a5fd2e78d79feeedb7a35914184`。原件 finish 自动分类为 auto/platform_only/pending，本候选据实际两处通用 guard 更正为 bugfix/false/none；补丁字节、配方和全部测试脚本不变。手写准备 diff 只留本地历史，不是交付补丁。

## H1 实际结果

| 范围 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| 原版有限缺陷/正常对照 baseline | 7 | 0 | 0 |
| 原 libs unittest discover | 7 | 0 | 0 |
| 原 svr unittest discover | 12 | 0 | 0 |
| 修后协议回归 | 7 | 0 | 0 |
| functional.py 包消费者 | 1 | 0 | 0 |

Conan verify 和官方 finish 内 W3 各自完整执行必要消费者、原 unit 与七组回归。交付按独立用例计 27（原19+新增7+消费者1），不因两次必要执行计54；baseline7是取证，不加入修后通过率；两项 --help 是调用，不另算消费者。

七组为真实 SIZE 后截短、text decoded 空 DATA、binary decoded 空 DATA、合法 SIZE=0/MD5、2049字节三块1024/1024/1及MD5、实际发送 CLI 截短 fail、实际接收 CLI 空块 fail。原版捕获有限 DATA0/SUCC0 与 steps=[0,0] 后用停止帧结束，不能称实测无限运行。修后 CLI 原 main 返回0，但实际发正确 fail、无继续空 DATA/SUCC0/MD5/Saved、未被看门狗杀死，因此不按 rc0 将传输误记成功。

完整自动 W3 exit=0，日志 SHA256 `3edc78d1ac81ebb268ae882816a103728224c21193fddf86ec7bb9ab4a26ab6b`；原始 .ci-result.json 未改字节，integrity_hash 与日志复算相符。所有18个记录 PID 已自然消失。详细入口和包 revision 见 [test-report.md](reports/test-report.md) 与 [h1-binding.json](reports/h1-binding.json)。

## 原始失败和工具边界

完整 finish 自然 returncode=1：step5b 全库知识字段/草稿错误并报告本 manifest 两条知识未引用；打印 Step8的 gen-summary（内部step6）另抛 `'str' object has no attribute 'append'`。另有 finalize RC2 的旧 packaging 缺失和 notes 无对话，以及内部step8提交材料预检的 test-report、packaging、.staging-verified 缺失提示。本候选补真实知识引用、对话决策和 test-report；没有重放软件测试/W3，没有手造 tar/marker，没有把原 finish rc1 改为成功。R19/R20 的旧 packaging/staging 适用性及全库 summary 阻塞由当前规则和准确证据另核。built 只表示本次实际 Conan 包构建验证，未发布。

Conan verify 报告 G0 未识别构建系统；G4 未定位 package ID，L2/L4/L5 实际跳过。保留原报告，实际包闭包及包内容检查由 H1 的准确 ref/cache path、消费者和包内摘要单独佐证，不将报告标题 PASS 当这些子检查已运行。

Windows 早期原 unit 因阅读副本缺真实目录链接发生导入 FAIL，后字节一致物化目录及原 discover 行为得到7/7和12/12；原版/修后定向各4通过3跳过。这些宿主历史不抹去，也不混入 OHOS 的无跳过结果。

## 发现与知识

- ✅ 已提取：[E429-draft-F6EC.kv](../../../../knowledge/drafts/E429-draft-F6EC.kv) 与 [配套文档](../../../../knowledge/drafts/E429-draft-F6EC.md)。记录 SIZE/remaining 条件、双端 guard、输入输出、正常对照、协议活动与文件进度的区别；仍为草稿，未进入正式索引或计分。

## 本次对话决策记录

用户/二级要求：固定原官方 Python 来源、真实三发行闭包和唯一 H1；H1 完成后复用未变结果，只处理本候选输入/引用与最低收口，保留完整 finish FAIL；最终候选还须有效独立 W4、真实 AtomCode 全差异检视及 B/P/C/F 和任务面板关联。

执行结果：只导入摘要核验过的 H1 配方/测试/官方补丁和原报告，更新实际结果与正确分类/引用。当前未取得 PR、Issue原生关系、面板关联、官方当前 head CI、AtomCode评论或有效提审。接受、合入与积分另核。
