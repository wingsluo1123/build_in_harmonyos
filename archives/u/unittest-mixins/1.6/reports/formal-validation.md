# 正式验证 w3-01：W3通过，完整Finish未通过

运行日期：2026-10-17。绑定提交：`6d37a7a4e363e9fa344174f8e52261479b2dc583`。运行仅启动一次；达到terminal并保留启动回执、WAL、原始日志、官方回执和资源释放证据。

| 项目 | 实际结果 |
|---|---|
| 冻结绑定 | 输入8741文件、工具2463文件、真实设备端点/boot ID/UID/进程身份 |
| 官方ConanVerifier | 返回0；G4包ID发现警告，L2/L4/L5未运行 |
| 完整W3 setup.sh + build_and_test.sh | 通过，1/1包成功 |
| 原版测试 | 31通过，0失败，0跳过 |
| 安装制品消费者 | 8/8通过 |
| 独立HarmonyOS HMDFS机制测试 | 1/1通过 |
| 官方L1e反证 | 真正移走lib后测试失败，确认依赖安装制品；随后官方工具恢复 |
| W3门禁 | L0/L1/L4/L5通过，L2无CLI跳过 |
| 官方.ci-result.json | exit_code=0，step=W3_local_ci |
| 完整Finish | exit_code=1，step5b知识检查失败 |
| 旧式G0 | configure不存在，exit127；不是Conan实际构建失败，原文保留 |
| 发布/远端CI/Review/提审/合并 | 尚未完成 |

W3原始日志SHA256：`33fec93534586e1d609d708ec47795e90362e2494f7f9d21949ba260423a4f73`。

官方回执SHA256：`157c498c4bc832cde340ceb82d105a3f505ca0e9b854b8baea32d6ef3a8ab2ce`。

完整Finish原始日志SHA256：`989f492d77a353c1aada2d0eb7b1fb1515acdbaa3196c10cefc18f878f5bb538`。

绑定清单SHA256：`840185ea724b984c4e0ec669b037bc1636010859910e48cd2678d0012bc0e9ca`。

W5失败根因：workflow_checks对KV逐行strip后仅取首行，忽略`root_cause: |`等字段后实际存在的续行，误报61个字段为空。该检查与仓库已有parse_kv_file解析器不一致。正式图谱没有修改；独立修复草案和正反回归证据保存在任务证据目录。manifest自己的引用缺口另行修复，不能据此宣称全局误判消失。

本次失败不可由覆盖状态、改回执或只重复step35消除。后续任何输入/工具调整都须在旧运行终态与释放证据保留后，建立完整新绑定，再执行完整Finish。
