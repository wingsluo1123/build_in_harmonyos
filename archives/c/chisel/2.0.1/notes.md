# chisel 2.0.1

## 编译说明

chisel 是 Facebook 出品的 LLDB 调试命令集合，用于辅助 iOS 应用调试。本项目为纯 Python 脚本集合，无需编译。

## 使用方法

安装后，在 ~/.lldbinit 中添加：
```
command script import /path/to/libexec/fbchisellldb.py
```

## 注意事项

- chisel 依赖 LLDB 和 Python 3
- 部分命令与 iOS 运行时相关，在 HarmonyOS 上可能不完全兼容
- 上游无官方测试套件，验证通过 Python 语法检查
---

**编译结束**: 2026-07-17 05:00
**最终状态**: published
