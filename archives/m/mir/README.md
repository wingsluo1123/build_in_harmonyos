# MIR

MIR 是解释器、C11 前端和原生代码生成库。本目录的 1.0.0 配方仅声明原生 HarmonyOS PC ARM64；发布库与公开头文件，不安装本次用于上游验证的命令行工具。

适配修复包括 OHOS libc/编译器系统头路径、musl wchar_t、私有可写临时文件、测试 API 对齐和 ARM64 懒编译回调的完整 SIMD 状态保存。后者同时覆盖首次函数调用与基本块生成两个入口，防止 128 位 long double 的高半部丢失。

上游原生测试清单为 7544 项独立执行身份：57 个 leaf 入口（含8个 bootstrap），以及七种 C2M 模式的全部原架构/选项合格 case。另有一个安装包消费者验证解释器、eager/lazy/lazy-BB 代码生成的冷/热调用，并在 OHOS 执行前检查 ELF 签名。具体终态、日志哈希及构建类型见版本报告；不能把探索性测试结果等同于正式 Conan 或比赛 CI。

## 依赖

无第三方 Conan 包依赖。原生构建使用 Python、GNUmake、Clang/LLVM、CMake 与平台 ELF 签名工具；运行时使用系统 libc、libm、libdl 和 pthread，不向系统库目录安装文件。上游说明和源码入口为 [vnmakarov/mir](https://github.com/vnmakarov/mir)。

## 使用边界

- Optional LLVM bridge 与 benchmark 不属于本配方已验证的原生套件。
- C11 前端读取非内嵌系统头时，使用 `C2M_SYSTEM_INCLUDE`、`C2M_TARGET_INCLUDE` 指定本机编译器的真实系统 include 目录；测试程序会从配置编译器探测，不硬编码其他机器的 SDK 路径。
- OHOS 系统头兼容层消去部分 Clang 声明注解。这不是 GNU 扩展实现；依赖 packed/aligned 属性、汇编符号重命名或 inline asm 语义的用户程序不在已验证支持范围内。
- 新增 ARM64 Q 寄存器保存不代表 SVE/SME 可伸缩向量支持，也不代表所有其他操作系统已验证。
- PR 合并、平台审核与制品仓发布是独立阶段，未发布前不保证远端可安装。
