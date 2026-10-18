# 安装后的 ELF 字节保持验证

完整旧基线的三个安装 smoke 都是 RC127，构建树消费者则可以运行。
实际 SONAME、版本实体及符号链接均存在。显式 `LD_LIBRARY_PATH` 或给同一 smoke
重新链接正确绝对 RUNPATH，仍无法加载安装库；不能据此归因“缺少库路径元数据”。

## 相同路径的字节对照

安装前缀、文件名、符号链接拓扑与权限保持，仅把版本共享库实体替换为 build/lib 的
原始链接字节。26 个库中 25 个模块安装副本曾被改写，DIY 库未改写。
替换后同一程序由 RC127 变为 RC0；原来没有 RUNPATH 的 smoke 配显式 LD_LIBRARY_PATH
也变为 RC0。SHA256 全表见 [install/byte-only-comparison.json](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/install/byte-only-comparison.json)。

`cont` 动态节显示链接 RUNPATH 是 `$ORIGIN:`，安装后为 `$ORIGIN`，程序头与节头布局相同。
这证实安装后的字节修改与不可加载之间的因果关系。ELF 含 `.codesign` 段，但未直接读取签名
校验结果，因此不把签名失败作为本次已独立证明的更细根因。
本次复用已有知识 E504/E077，不另申报新知识。

## 标准 CMake 修复

在生成 toolchain、创建上游目标前设置：

```python
tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
```

上游模块额外追加 `$ORIGIN`。测试程序在 build/bin，库在 build/lib 和 install/lib，
相对路径同时成立；首次链接即使用最终 RUNPATH，安装无需改写。
[CMake 官方变量说明](https://cmake.org/cmake/help/v4.4/variable/CMAKE_BUILD_WITH_INSTALL_RPATH.html)
规定此变量初始化目标的 BUILD_WITH_INSTALL_RPATH 属性，因此必须在创建目标前设置。
默认配置没有额外 Conan 共享依赖；未来启用外部后端须独立处理其运行路径。

重配置/重链接的控制实验得到 26/26 真实共享库安装 SHA256 与链接 SHA256 相同，
三个安装消费者及 fixture/准备/清理 7/7 通过，见 [install/rpath-fix-result.json](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/install/rpath-fix-result.json) 与
[install/rpath-fix-smokes.xml](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/install/rpath-fix-smokes.xml)。这些是修复机制实验，不冒充最终全新 create。
最终实际 Conan 包及新前缀、隐藏原包的消费者结果另见 [installed-result.json](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/installed-result.json)。
