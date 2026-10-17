# multimon

multimon 是一个多协议无线电信号解码器，并提供配套的测试信号生成器 `gen`。它可以从原始 16 位 PCM 文件或流读取采样，解码 DTMF、POCSAG、AFSK、ZVEI 等格式。

## HarmonyOS 适配

- 使用 HarmonyOS clang 在 AArch64 真机原生构建。
- 通过已发布的 `libx11/1.8.13` 提供上游显示模块依赖。
- 修复现代 C 内联链接语义兼容性。
- 修复 FIFO/管道奇数字节短读导致 16 位 PCM 永久错位的问题。
- 使用安装后的 `gen` 和 `multimon` 完成分片继承管道端到端消费者验证。
- 对最终 ELF 原位签名，并检查 `.codesign`、RPATH/RUNPATH 与路径可迁移性。

## 依赖

- `libx11/1.8.13`
- `xorgproto/2025.1`

## 参考资料

- 官方项目页：https://sourceforge.net/projects/multimon/
- 官方 1.0 源码：https://sourceforge.net/projects/multimon/files/multimon/1.0/
