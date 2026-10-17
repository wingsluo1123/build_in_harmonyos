# E429 草稿 — SIZE 尚未完成时，decoded 空 DATA 与 SUCC0 不代表文件进度

来源是官方 Python trzsz 1.1.5 commit `e433a8c326dddd1b7a9fe79f3f1b766f76fe9ca8`，账号 orrkri 主活动任务 11309；与 trzsz-go 无关。本稿由官方 `graph add E429 --draft` 生成骨架后补齐，尚未提升、接受或计分。

在已经约定正 SIZE 的文件传输中，每个“成功块”必须推进文件字节数。原版若读取真实 EOF 后仍发送 decoded 空 DATA，接收方返回 SUCC0，双方 `step` 保持不变。每块接收及时结束并取消 alarm，下一块再设置 alarm；这可以有持续协议活动，却没有业务进度。Windows 与本次 OHOS H1 均只观察有限零进度前缀，再由停止帧结束；没有将该取证称作实际无限运行或自然完成。

## 条件、症状和输入输出

发送方先用 `os.path.getsize` 发 SIZE，再读取文件；普通源文件可以在 SIZE 确认后被另一操作截短，`read()`真实返回空 bytes。接收方也可能在 `remaining > 0` 时收到有效空 DATA。文本模式的空内容经过 zlib/base64 后，wire 帧本身仍非空；binary 模式为 `#DATA:0`。检查对象是解码后的数据，不是 wire 行是否为空。

定向回归的原版输入是实际 128 字节临时文件，在真实 SIZE 确认后截短至 0；有限对端先给 SUCC0，再给 fail 停止帧。实际输出显示两次空 DATA、`steps=[0,0]`，没有 MD5 完成。接收端原文本 parser 输入有效空 DATA 与停止帧，实际回 SUCC0 且 `steps=[0,0]`。人为停止只界定取证范围，不能当自然终态。

修后相同阶段的直接库错误分别为 `Unexpected end of file`、`Received empty file data`，均使用原 `TrzszError(trace=False)`。CLI main 会捕获错误后调用 `server_error` 发 `#fail`，原代码没有显式非零退出；本次 OHOS 的两个真实 CLI 已核具体 fail 消息、无继续 SUCC0/MD5/Saved、自然有限返回且未触发测试看门狗；不能只看 rc。

## 最小修法与使用

在 `transfer.py::send_file_data` 的 `while step < size` 内，读结果长度确定后、`send_data` 前拒绝空 bytes。接收方在 `recv_file_data` 同一循环内，`recv_data` 返回后、写文件与 ACK 前拒绝空 bytes。通过原错误路径通知对端。不要重新降低已约定 SIZE 来称完成，不需要全局禁用空控制帧。

本任务提供同版 metapackage、libs、svr 三份正常发行元数据和 modules。Conan runenv 下复现：

```sh
python3 progress_regression.py
```

原版同一完整源码及 namespace 进入 import path 后，使用同脚本的 `--baseline`。该模式 PASS 只表示捕获原缺陷；它用有限停止帧，不宣称原程序自然完成。正向用真实 SIZE/数据/MD5函数核合法空文件及 2049 字节三块（1024/1024/1）内容一致。两个原 unit discover 入口保留，定向回归不替代它们。

## 可迁移范围与近邻增量

适用于明确长度约定且空块不是合法流控状态的事务。迁移时先核当前阶段、remaining、协议对空块/EOF的定义，再在成功确认前建立正业务进度不变量。合法 SIZE=0 不进入数据循环；通用零长控制帧、等待流增长的协议和长期服务不能套此 guard。

| 近邻 | 已覆盖 | 本稿新增边界 |
|---|---|---|
| E464 / MyGUI | read 忽略 gcount、EOF虚报非零，按 size 读并修资源接口 | trzsz 的 read 已真实返回0且已有 SIZE；decoded DATA0/SUCC0 仍被双方接受，需双端错误分类 |
| E361 | 超时后的执行清理与 canary | 每块消息及时完成仍可取消并重设 alarm，须核文件字节进度 |
| E214 | 非交互 stdin 等待 | 已有积极协议流量，改终端检测或跳过 read 不能解决 |
| KGame Issue3136 | 按 close 消息设计的长期进程 | 正 SIZE 文件事务应完成或报错，不能把外层 TERM 白名单当文件成功 |
| zrepl Issue3694 | 无限 shell producer 与外部写端 SIGPIPE | 本题无 shell producer/fork 根因，成功 ACK 自身无法保证进度 |

近邻来自当前 main `1262b4ac24a3244f254c3e8163fa35d04b48f7fb` 全文及领前两次独立核对；不声称穷尽所有 PR/别名。普通 Python 包装、termios 可用性和 timeout 运维不是所申报的增量。

## 匹配入口和限制

当前官方 engine 的 Phase B 对 `error_signature` 按 `|` 分割后做固定字符串包含匹配。本 KV 使用真实回归 JSON 的 `"steps": [0, 0]` 与两条明确 guard 错误；没有把正则文本交给固定字符串消费者。关键词限定本回归的负向案例及这两条错误。正常空文件的 `steps=[0]`、正常多块进度及 SUCC0 在 SIZE=0 阶段均不能单独判此故障。

代表性 Windows 原始日志经官方 parser 和实际 engine 在临时隔离索引中执行：原版两个负向样本 Phase B 得分6，修后两个明确错误样本得分7；合法 SIZE=0、正常三块及合法零 SIZE 的 SUCC0 控制样本均不命中签名、Phase B 得分0。本次另核10条 H1 原始 baseline/修后 W3 日志及1条人工合法 SIZE=0/SUCC0 对照（合计六个负向、五个正常）：六个签名命中，五个 Phase B 为0。完整 engine 对这些正常样本仍返回 Phase A 模糊推荐，因此 `engine_matched=true` 本身不是该缺陷诊断或负向命中。

出现重复零 step 后仍需核“正 SIZE 尚未完成”条件，不能泛化所有重复回调；通用 `Unexpected end of file` 还须确认 trzsz 文件阶段来源。草稿尚未进入正式索引，代表性检查只检验真实解析和匹配机制，不能冒称全库已登记或自动修复。

## 已有证据与待验边界

Windows/Python 3.11.0rc2 上，原版与修后各执行 7 组中的 4 组，失败0、跳过3；binary 和两项 POSIX CLI 明确未测。原 unit 7/7、12/12；Windows 用字节一致目录副本解析原测试链接，原 tar 为目标保留真实 symlink。首次缺这些链接导致的导入 FAIL 保留，没有删原断言或将失败改通过。

完整 commit 归档和三 sdist 均已下载复算；三发行必需模块与 commit 逐字节一致。唯一 H1 在 OHOS6/armv8 上实际使用精确公共 Python 3.12.9 闭包：原版 baseline7/7、原 unit7/7与12/12、修后回归7/7（含 binary 和两个真实 CLI）、包消费者1/1，均无跳过。消费者核真实包模块、三发行元数据和 OHOS termios；协议回归实际执行 alarm。完整自动 W3 exit=0，日志 SHA256 `3edc78d1ac81ebb268ae882816a103728224c21193fddf86ec7bb9ab4a26ab6b`。受测官方补丁 SHA256 `2fe5709f5680428cfc7bcd12e2b58982450f5ddb6abfb06636a17f98e3938335`，包内 transfer.py SHA256 `1c3e5318de04c58446fcb0fa80dfcaa882b39a5fd2e78d79feeedb7a35914184`。完整 finish 仍自然rc1（知识预检和提交材料检查），没有把 W3 通过当完整收口。详情见 [软件测试报告](../../archives/t/trzsz/1.1.5/reports/test-report.md)。W4、AtomCode、官方当前head CI和有效提审仍待准确回执。

修法不承诺残件删除、原子写入、旧文件保全、任意恶意输入处理，未扩大到接收块超过 remaining 或源文件增长的其他缺陷。没有受测自动修复实现，`rec_auto_fix=false`。软件测试、PR、知识接受、合入和积分分别登记。
