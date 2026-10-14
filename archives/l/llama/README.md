# llama.cpp

llama.cpp 是用纯 C/C++ 实现的大语言模型(LLM)推理引擎,基于自带的 ggml 张量库,
可在 CPU(含 ARM NEON)上运行 LLaMA 系列及众多主流开源模型,无需 GPU。

## 功能概述

- `libllama`:核心推理库(tokenizer、采样、grammar 约束解码、上下文管理)
- `libggml` / `libggml-base` / `libggml-cpu`:张量计算后端(AArch64 NEON 内核)
- `llama-cli`:交互式/一次性文本生成命令行工具
- `llama-server`:OpenAI 兼容 HTTP API 服务(内置 WebUI)
- `llama-quantize` / `llama-bench` / `llama-tts` / `llama-mtmd-cli` 等配套工具

## OHOS 适配

- **CPU 指令集**:上游默认 `-mcpu=native` 探测,适配中强制 `GGML_NATIVE=OFF`,
  经 `GGML_CPU_ARM_ARCH` 指定目标架构(默认编译器基线 armv8-a),保证产物可复现
- **ELF 签名**:产物 .so 补 DT_SONAME 后需重新自签,否则鸿蒙 XPM 拒绝 dlopen
- **WebUI**:预编译资产来自 HuggingFace,离线构建降级为内嵌空 UI,server HTTP API 不受影响
- **测试**:tokenizer 测试所需词表模型已随源码树提供,ctest 套件可完全离线运行

## 依赖关系

- 编译依赖:无(第三方库全部 vendor 在源码树内)
- 可选依赖:OpenSSL(仅 llama-server HTTPS,默认关闭)

## 参考资料

- 官方仓库:https://github.com/ggml-org/llama.cpp
- 许可证:MIT
