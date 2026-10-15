# libuninum

libuninum 是把多种 Unicode 数字表示与任意精度整数相互转换的 C 库，并提供
numconv 命令行程序。

支持数字系统识别、中文数字规范化及多种数字系统的双向转换。任意精度计算
依赖 GMP；Tcl 是原始测试脚本和可选交互工具的运行依赖，不是 C API 消费者的
强制运行依赖。

HarmonyOS PC 使用原生 Clang/LLVM 构建。公共 UTF32 类型仍为 unsigned long，
消费者不得假设它与 wchar_t 或 uint32_t 的内存布局相同。LP64 内部宽字符长度
和规范化容量修复见 2.7.1；CLI 的旧输入输出修复继续保留。

2.7 是已发布的上游版本；2.7.1 是同一上游版本的适配修复号，尚未发布。
修复版本需经过独立 PR、平台 CI、评审和正式发布后才可供下游引用。

上游：https://www.billposer.org/Software/libuninum.html

构建配置、测试和修复证据见对应版本的 conanfile.py、notes.md 与 reports/。
