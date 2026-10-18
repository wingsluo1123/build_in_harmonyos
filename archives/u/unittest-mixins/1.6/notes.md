# unittest-mixins 1.6 适配记录

本依赖用于 coverage 5.0.4 的完整测试。原始父项还包括 PyJWT、oauthlib、requests-oauthlib 和 mwclient，均保留在独立任务台账中；本库正式发布且目标消费者验证后才恢复父项。

## 原始失败与处理

- 新鲜 HarmonyOS host/build 图及 `--build=never` 确认 unittest-mixins/1.6 未发布，six/1.17.0、setuptools/84.0.0、pytest/9.1.1 的目标二进制可用。
- PyPI 元数据 requires_dist 为空，源码 setup.py 实际声明 six>=1.4.0。配方按源码声明运行依赖 six/1.17.0。
- 原始测量命令 `python3 -m coverage run -m pytest` 因 coverage 缺失失败。上游 tox 的 coverage 仅用于测量；.coveragerc 没有 fail_under 或测试守卫。未修改该配置，也未宣称覆盖率测量通过。
- 原版 31 项分别经 stdlib unittest 和已发布 pytest/9.1.1 执行均通过，保留原断言、原参数化与原守卫；不将内部故意触发的失败场景重复计数。
- 最初 test_package 错用 tested_reference，导致消费者配置失败。修正为 Conan 2 的 tested_reference_str 后，对同一真实制品运行 conan test，消费者8/8、独立平台1/1通过；原始失败日志保留。
- 为满足官方 Verifier 合同，后续增加标准 export_conandata_patches / apply_conandata_patches 入口；无源码补丁。此后配方需绑定新的正式验证，旧制品证据不冒充新输入验证。

## 发现与知识

测试辅助包与测量工具可能存在测试工具依赖环。运行依赖图、测试断言执行图与测量工具图需分别核验，只有原版测试全量运行、源码哈希一致且无覆盖率阈值或守卫被绕过时，才能将测量工具缺失单独报告。正式资格及新知识入库待官方审核。

HMDFS 的权限位受挂载策略归一化影响；本任务仅复用已有平台知识，不将其更名为新知识。独立平台测试直接读取 mountinfo 并验证 chmod 后实际写入与清理，不使用 mock。

## 状态

本地原生验证31项、安装消费者8项、平台机制1项已通过。正式w3-01的完整本地CI已通过，完整Finish因检查器误判未通过。当前知识引用元数据已更新，需要完整新绑定；远端CI、Review、提审、合并及发布均未完成。


官方 ConanVerifier 对标准补丁入口新增后的配方已返回0（2026-10-16）。其 conan create 原始日志再次证实上游31/31、消费者8/8和独立HMDFS1/1。官方报告G4提示无法找到包ID，L2/L4/L5因此未执行；不能把工具总体PASS解释成这些检查实际执行。独立载荷清单、官方sdist逐字节比较及安装来源检查另存；当时尚未启动正式W3，后续记录见下方。

## 正式运行 w3-01 的终态（2026-10-17）

绑定提交6d37a7a4e363e9fa344174f8e52261479b2dc583，完整输入与工具/设备身份已冻结，一次启动并达到终态、子进程已等待退出及资源释放。官方setup和完整build_and_test执行成功，原版31/31、消费者8/8、独立HMDFS1/1；移走真实包lib后的L1e反证通过。官方.ci-result.json记录exit_code=0，完整W3日志SHA256为33fec93534586e1d609d708ec47795e90362e2494f7f9d21949ba260423a4f73。

完整Finish返回1：W5用逐行正则读取KV，误将主分支775条知识中61个合法多行字段判为空，尽管官方graph validate通过。另有本任务manifest未引用知识草稿的问题，现已补上真实knowledge_ref。未伪造通过、未修改正式图谱、未重放该运行；框架检查器修复须独立处理并建立完整重新绑定后继。

旧式G0实际对纯Python sdist调用不存在的configure并返回127，按官方流程继续由ConanVerifier验证。G0失败原文保留，不能称所有门禁实际执行且通过。路径B草稿只是候选；官方资格、审核、合并、发布仍未完成。
# 冻结前历史与类型说明

w3-01保留完整Finish失败；w3-02在仅含KV修复的框架上完整Finish/W3返回0。随后同步主分支、增加PF9框架修复、补齐配方入口说明及LF行尾，必须建立新的完整绑定，不能继承这两轮历史回执。当前HEAD的正式绑定、官方回执、远端CI与提交状态在PR中单独回读。

本包仅安装Python源码、egg-info与许可证，未提供C/C++链接库。保留package_type=unknown，并在requires/test_package中明确headers=False、libs=False、run=True，实际安装消费者验证运行环境传播。代码规范中的C/C++ library示例适用性单列为待官方确认项，不为消除风格提示盲目改变Conan依赖traits。

## 结束

归档状态为 built，尚未正式发布。软件提交3f390414455122e5e35123466e3e8cac33af0b61的完整w3-05已在独立本地框架7cfc213e2f3c9bdc247f227183a86d2f976f187c上通过；该框架修复PR已按用户要求关闭、未合入主分支，不能据此宣称远端CI或提审门禁通过。本次补齐归档结束说明后，当前提交仍须完整新绑定；原测量命令及前文各项警告保持未验证或警告状态。原始绑定、回执、日志与释放证据保留在独立交付目录，后续进度据实在软件PR及任务台账更新。
