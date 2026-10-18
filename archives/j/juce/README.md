# juce

JUCE — cross-platform C++ framework for audio and graphical applications.

- 主页: https://juce.com/
- 上游: https://github.com/juce-framework/JUCE
- 许可: AGPLv3 / 商业 (JUCE 9 licence)

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 9.0.3 | built | HarmonyOS PC (aarch64) 适配; header+module-source 框架分发, 消费者编译模块源 |

## HarmonyOS 适配要点

- 模块为 INTERFACE 库: 包安装全部模块头+源码+CMake 支持文件, 消费者按需编译模块源
- OHOS 裁剪: cpp_info.defines 强制 JUCE_USE_CURL=0（sysroot 无 libcurl）
- 补丁: pthread_cancel OHOS 守卫 (E127)
- 消费者必须定义 JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1

详见 9.0.3/notes.md 测试台账与知识候选台账。
