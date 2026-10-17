# multimon 1.0 适配笔记

## 构建环境

- 目标：HarmonyOS PC / armv8 / Release
- 编译器：HarmonyOS clang 15
- 构建系统：上游 Makefile，由 Conan 显式传入编译器、依赖路径与通用 AArch64 选项
- 依赖：`libx11/1.8.13` 已发布 OHOS armv8 共享制品；`xorgproto/2025.1` 提供消费时必需的 X11 协议头

## 适配内容

1. 将头文件中的 GNU89 `extern inline` 定义改为标准的翻译单元局部 `static inline`，避免现代 C 内联语义产生重复定义。
2. 让构建期执行的 `mkcostab` 使用 build-machine 编译器，目标程序仍使用 HarmonyOS clang，避免交叉构建执行目标 ELF。
3. 不采用上游 Makefile 为未知架构设置的 i486 选项；配方显式传入 HarmonyOS clang 与通用 C11 选项。
4. 修复原始 16 位 PCM 文件/管道输入：跨 `read()` 保存 1 字节残余，只提交完整样本；干净 EOF 成功，半样本 EOF 明确失败。
5. 打包并签名 `multimon` 与 `gen`，拒绝 RPATH/RUNPATH 及构建机绝对路径。

## 验证范围

官方 1.0 源码没有自动化测试套件。新增四个安装后消费者场景：生成并解码规则文件、经继承匿名管道在首字节后分片写入的端到端解码、干净 EOF、半样本 EOF。管道场景先启动包内 `multimon`，再写入首字节，用 `FIONREAD` 确认其已被单独取走后才写余量；它通过 `/proc/self/fd` 运行包内 `gen` 和 `multimon`，不是对提取函数的模拟。

`raw` 路径是本次生产运行验证的输入路径。上游对其他音频格式的支持由外部 `sox` 命令提供，不属于本软件的链接依赖，也不计入本次测试通过数。

## 交付物

- `bin/multimon`：多协议解码器
- `bin/gen`：测试信号生成器
- 上游各源码文件携带 GPL-2.0-or-later 许可证声明；官方归档本身未附独立 `COPYING` 文件
