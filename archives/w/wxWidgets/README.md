# wxWidgets

## 简介
wxWidgets 是一个成熟的开源跨平台 C++ 框架，提供 GUI 和其他开发功能。它允许开发者使用单一的代码库在 Windows、Mac OS X、Linux 和其他平台上编写应用程序。

## OHOS 适配

### 适配要点
1. **构建系统选择**：autotools 在 HarmonyOS 上失败（config.status 无法创建），必须使用 CMake
2. **平台检测**：需要修改 `build/cmake/toolkit.cmake`，添加 HarmonyOS/OpenHarmony 平台检测
3. **libc 能力检测**：复用 wxWidgets 的 CMake 编译测试，针对目标 sysroot 探测标准 resolver 函数及可用的 `_r` 变体
4. **类型检测**：复用 `wx_get_socket_param_type()` 探测 socket API 所需的 `socklen_t`、`size_t` 或 `int`，不按平台名硬编码

### 已知问题
- GUI 功能目前禁用（`wxUSE_GUI=OFF`），只编译基础库和网络库
- xlocale 功能禁用（musl libc 不支持 locale 扩展函数）

### 与 Linux 的差异
- HarmonyOS 使用独立目标 sysroot，实际 libc 接口以 CMake 能力检测结果为准
- 缺少某个 `_r` 变体时，wxWidgets 会使用其互斥保护的非重入 fallback

## 依赖
wxWidgets 基础库无外部依赖，内置了：
- zlib（压缩）
- PCRE（正则表达式）

## 功能验证
```bash
# 检查库文件
ls ~/usr/local/lib/libwx*.a
# 应输出：base/net（OHOS 后缀）、regex、expat 和 zlib 静态库

# 验证网络库符号
nm ~/usr/local/lib/libwx_baseu_net-3.2.a | grep gethostbyname
```

## 参考
- 官网：https://www.wxwidgets.org
- 源码：https://github.com/wxWidgets/wxWidgets
- 文档：https://docs.wxwidgets.org/
