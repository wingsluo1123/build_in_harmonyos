# pawk 0.8.1 最小适配准备

来源为固定PyPI sdist，SHA256 `59ec1a4046cf545e1376c8c0a28f5f178a3b88dbc85fb3772aa3ce8c2e088349`。其pawk.py与上游v0.8.1 commit `d60f78399e8a01857ebd73415a00e7eb424043ab` 字节相同。发行/tag为0.8.1，内部版本为0.8.0，未改版本。

sdist不含原测试和许可证文件；配方导出固定上游未改的 `pawk_test.py` 与 `COPYING`。九个原测试函数为3个Action单元测试和6个集成测试，均含真实assert；原文件 `__main__` 执行benchmark，新增runner显式调用九函数并校验原文件SHA，禁用优化模式，任何失败返回非零，不冒称pytest。

`Context.from_options` 在 `-F/-O/-L` 上将已解码Python str直接传给unicode_escape，隐式UTF-8转换后再次解码会损坏非ASCII。三行修复先encode(raw_unicode_escape)，保留字面文本和原ASCII反斜杠语义。主机原件已有汉字-F失败及修复后的汉字-F、字面\\t-F、é-O、汉字-L成功；这是跨平台文字层问题，未宣称OHOS独有。

PAWK9336-H1-001 在 OpenHarmony aarch64 / Python 3.12.9 取得原生补丁生成、独立应用核验、Conan create、九原函数9/9和安装包消费者1/1通过。消费者覆盖4场景/4次CLI调用/12条功能assert与2条身份assert。补丁SHA256为 `4c30ca232ca6b7c696ea93d46e31b2da6741ee06754bce76b13fb56d001af86b`，受测模块SHA256为 `f39d7e4eee06d26d0962baaffacc7d01566a53d21eab21d8c266ca27c96192b5`。复用原结果，没有重跑九函数或消费者。

旧H1-001完整finish rc1保留：独立G0 clean-verify缺源包上下文；旧W3 setup0/build1，在全树JC1/JC5发现官方固定基线中其他软件的8个状态文件，pawk构建跳过。Conan verify的G0为风险预查询，不能替代独立clean-verify；其G4未找到包ID、L2/L4/L5跳过，不逐门记真实执行通过。G0工具固定调用configure/make，而本sdist没有这些入口；官方将clean-verify列为非阻塞，源包上下文已补，原失败和适用性说明保留，没有重跑完整finish。

随后原唯一H1对固定17文件输入执行首次缺失完整W3（orrkri-9336-pawk-W3-002），自然rc0。其内部真实Conan create、九原函数9/9和安装消费者1/1通过，与旧001结果分别留存；本作者未手动重播。L0/L1/L4/L5实际PASS；L2实际为 `skip: pawk version/help failed`，脚本标非阻塞，stderr被原脚本重定向，具体原因未取得，不推定为软件通过或平台失败。消费者通过的是指定Conan Python/环境中的wrapper调用，不能证明裸shebang入口version/help通过；该边界交正式审阅判断。

W3生成的ci-metadata将build_trace.commit记为unknown；证据以固定输入指纹、完整17文件差异和官方ci-result/log摘要绑定，不补造受测commit。首次源码预下载警告后实际Conan download/create成功，警告仍保留。W3 rc0不等于整体READY、远端CI或有效提审。

首次主机pytest缺安装失败及后续九函数直接调用成功分别保留，不称pytest。独审、完整AtomCode、远端CI与有效提审仍待证。

目标验证只用一个安装包消费者程序，含4个既定场景/4次CLI调用/12条功能assert与2条包身份assert；计数为1消费者，不能当4或14个新测试。原9测试与该消费者不重计。消费者执行本次包的入口文件并验证本次安装模块路径，保留内部0.8.0事实。失败或非运行环境返回非零。

依赖固定Python recipe revision `d8eda770878152bea40b42db9f7024cd`；已有同目标精确包下载rc0可复用作准备依据，不能替代本候选目标运行或官方clean CI。H1由二级调度原唯一执行者；本候选不得手造ci/audit PASS状态。
