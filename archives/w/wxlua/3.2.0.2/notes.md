# wxLua 3.2.0.2 适配记录

## 任务与源码

- 平台任务 #12016；分支 `feat/wxlua-3.2.0.2`。
- main 基线 `64ef90131f8bcf215b3d94903de4484e2b8fb5b1`。
- 上游 tag v3.2.0.2；官方 codeload tar.gz，SHA-256 `62abe571803a9748e19e86e39cb0e254fd90a5925dc5f0e35669e693cbdb129e`。
- 语言预检通过，主体为 C/C++；Lua 文件含绑定生成器、示例和测试。
- 构建系统采用上游 wxLua/CMakeLists.txt；根目录 Makefile 导致 init-build 自动识别为 autotools，已按源码修正。

## W0 依赖核验

`wxwidgets/3.2.10` 仅为 wxBase，强制关闭 GUI，不能满足 wxLua 核心的 wxWindow/销毁事件契约。经制品仓别名检索发现 GUI 变体 `wxwidgets-gtk3/3.2.10` 已发布，不重复申报。GUI 变体与 Lua 5.4.8 均实际下载到 OHOS ARM64 二进制。

仅使用 ohpcd 的 `conan install --requires=wxwidgets-gtk3/3.2.10 --requires=lua/5.4.8 --build=never` 安装成功，22 个依赖包可用。首轮私有缓存默认启用了 ConanCenter，导致混入不适用的配方及 pixman 版本冲突；禁用该远端并从 ohpcd 更新后解决。不是缺失依赖，没有自申自领项。

## 适配实现

唯一源码补丁为可选的 CMake config target 接口：用 imported target 承接 wxGTK 完整传递依赖，保留传统 FindwxWidgets 路径。构建全部可用绑定与三个上游应用；gl/media/webview 在发布的 wxGTK 依赖中不可用，显式禁用并公开范围。

Conan 定义公开 library 契约，同时声明软件级 commands.json。库顺序、头目录、宏定义必须通过独立消费者验证。测试子进程单独应用 GTK 动态库路径，避免污染主机 Python 的 libintl。

GitHub 镜像注入流程首次下载未完成；改用已校验的官方 codeload，并显式给 `get()` 传 tar.gz 文件名，避免无扩展名被当成 zip。

## 上游测试清点与探索实测

wxLua 自身正式测试入口为 `samples/unittest.wx.lua`，运行时计数 98。该文件未改动，额外驱动要求 tests_run=98、failed_tests=0 和完成标记，不能以退出 0 代替测试结果。目录内 vendored Lua 5.1 的示例测试不属于本次所构建的外部 Lua 5.4.8，未统计为已运行。其余 samples 是交互示例，不冒充自动化测试。

探索构建：库、Lua 模块、wxLua/wxLuaCan/wxLuaFreeze 均编译成功；上游 98/98；GUI/Lua 消费者 10/10。真实浏览器经私有 Broadway 显示窗口、中文文本；点击按钮使 callback count 从 0 到 1。

独立探索消费者实测：C++ 4/4；Lua 5.4 宿主通过真正的 require("wx") 加载模块并调用 wxString，1/1。合计消费者 15 项。预审发现的许可证遗漏、Lua 搜索路径分隔符错误已修复，删除未使用的空壳测试文件，并限定实际支持的静态/PIC 配置。

首轮正式 Conan 构建在 -O3 下超过工具 3600 秒限制，日志为 TIMEOUT，不能视为下载失败或测试通过。Release 调整为 -O2 以控制生成式绑定翻译单元的编译成本。2026-10-06 正式收尾：conan-verify G0–G4 PASS，本地 W3 CI 门禁通过（.ci-result.json exit_code=0），manifest 状态 built。

## A/B 判断

按路径 A。E527 已覆盖 Broadway；E447 已覆盖旧 Find 模块与 CMakeDeps 传递依赖；E221 已覆盖 CLI 与公开库契约。本次没有足以支撑 B 的独立新知识，不重复提交知识贡献。无确认缺失依赖。
---

**编译结束**: 2026-10-06 14:14
**最终状态**: built
