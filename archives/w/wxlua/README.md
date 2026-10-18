# wxLua

wxLua 3.2.0.2 提供 Lua 5.4 与 wxWidgets 3.2 的绑定、公开 C++ 库、Lua 动态模块及 wxLua、wxLuaCan、wxLuaFreeze 应用。

## HarmonyOS 范围

使用已发布的 `wxwidgets-gtk3/3.2.10` 和 `lua/5.4.8`。图形界面由 GTK Broadway 通过 HTTP/WebSocket 显示到浏览器，不是 ArkUI 原生窗口。支持 stc、xrc、richtext、propgrid、html、aui、adv、core、xml、net、base。依赖未提供的 OpenGL、媒体和 WebView 绑定不构建；不宣称这些可选功能通过验证。

## 构建与测试

```sh
conan create archives/w/wxlua/3.2.0.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd
```

配方自动启动只绑定回环地址的私有 Broadway 服务，运行上游 98 项断言并要求零失败。test_package 验证 GUI/Lua 事件、C++ 公共库和动态 Lua 模块，服务在测试结束后退出。测试需要可执行目标平台二进制的 HarmonyOS PC 环境。

## C++ 消费

```cmake
find_package(wxlua CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE wxlua::wxlua)
```

头文件为 `wxlua/wxlua.h`。使用 `CMakeDeps`、`CMakeToolchain` 与 `VirtualRunEnv` 传播依赖；不要手写 Conan 缓存绝对路径。

## Lua 和 GUI 使用

在 Conan 生成的运行环境中启动 GTK 依赖的 `broadwayd`，例如 `broadwayd -a 127.0.0.1 -p 8080 :1`；设置 `GDK_BACKEND=broadway` 和 `BROADWAY_DISPLAY=:1` 后运行 `wxLua your-script.lua`，在同机浏览器打开 `http://127.0.0.1:8080/`。使用独立 `XDG_RUNTIME_DIR` 可隔离并发任务。跨机器访问应使用用户自己的安全转发。

Lua 模块安装为 `lib/lua/5.4/wx.so`，须由 Lua 5.4 宿主导出 Lua C API。静态 Lua 宿主需要将 Lua API 纳入动态符号表；test_package/module_host.c 展示真实加载和调用方法。Conan 的 Lua 依赖是开发库，不假设其附带 `lua` 命令。

上游：<https://github.com/pkulchenko/wxlua>。许可证随包安装。
