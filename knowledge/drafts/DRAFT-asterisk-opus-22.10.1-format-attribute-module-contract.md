# DRAFT — Asterisk Opus 不是单一库：格式属性模块与编解码模块的交付契约

> 状态：DRAFT，待主编审核。来源：Asterisk 22.10.1 上游源码树。

## 结论

`asterisk-opus` 任务的直接目标是 `res/res_format_attr_opus.c` 生成的
`res_format_attr_opus.so`。该模块注册 `ast_format_interface`，处理 Opus
格式属性和 SDP `fmtp` 参数；它不实现音频编码/解码，也不调用 `libopus`。

`codec_opus` 是另一个职责边界。它可以是运行时所需的配套模块，但不应被
错误地打进本配方，也不能把本配方描述成“提供 Opus 编解码能力”。

## 为什么容易误判

- 任务名含 `opus`，但 Asterisk 源码将格式属性和 codec 实现拆成独立模块。
- `res_format_attr_opus.so` 的依赖是 Asterisk 模块 ABI，而不是外部 `libopus`。
- 复制其他音视频包的配方会自然引入 `libopus`、编码回环测试和错误的产物名。

## 推荐适配口径

1. 先从上游源文件、`MODULEINFO`、`AST_MODULE_INFO` 和 menuselect 条目确认
   目标模块。
2. 只构建并打包 `lib/asterisk/modules/res_format_attr_opus.so`。
3. 补齐 Asterisk 顶层 configure 所需的基础依赖，但不把 `libopus` 写进
   该模块的链接依赖，除非目标版本的模块源代码确实调用 `opus_*` 符号。
4. 消费者测试检查真实 ELF 产物和模块描述字符串；实际编码/解码属于
   `codec_opus` 的另一个测试契约。

## 适用范围

该判断方法适用于 Asterisk 及类似模块化工程：包名只表示功能族，不能替代
源文件和模块注册点。凡是“某功能”的任务，都应先区分格式/协议适配层、
核心 ABI 模块和真正的第三方算法库。

## 与已有 Opus 条目的差异

知识库已有的 `DRAFT-opus-1.6.1-cmake-rtcd-harmonyos-presume` 讨论的是
独立 `libopus` 的 CMake ARM CPU 检测；本条讨论 Asterisk 的模块边界和
消费者交付契约，触发面、修复面和验证对象均不同，不是重复条目。
