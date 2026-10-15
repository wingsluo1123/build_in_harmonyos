# wxwidgets-gtk3

wxWidgets 3.2 的 GTK3 GUI 变体，为 HarmonyOS PC 提供 wx GUI 能力
（wxCore/wxAdv/wxHtml/wxAUI/wxSTC 等 GUI 库），是 codeblocks 等
wx 系 GUI 应用的前置依赖。

适配修复版本 `3.2.10.1` 默认使用共享库，使应用主程序、SDK 与插件共享 wxApp 等全局状态。
单模块静态消费者仍可显式设置 `wxwidgets-gtk3/*:shared=False`。
共享模式的 Conan 元数据仅包含已安装的库，并定义 `WXUSINGDLL`。
原生 OHOS 安装后的 ELF 在最终路径签名；`wx-config` 通过常规脚本解析
当前包目录，避免引用发布机器的构建缓存。

与 `wxwidgets`（base 变体）的区别：base 只构建无 GUI 的 wxBase 库；
本包以 `wxUSE_GUI=ON + wxBUILD_TOOLKIT=gtk3` 对接制品仓 `gtk/3.24.43`
（broadway 后端）。wx 3.2.10 GTK 端口中所有 X11 专有代码均有
`GDK_WINDOWING_X11` 编译守卫，在 broadway 后端下编译为空，因此无需
X11/Wayland 客户端库即可完整构建 GUI 库集。

- 上游: https://github.com/wxWidgets/wxWidgets
- 许可: wxWindows Library Licence
- 上游版本: 3.2.10；当前适配修复版本: 3.2.10.1。已发布的 3.2.10 静态配方保留。

GTK 提供有效屏幕尺寸但未填充单监视器尺寸时，回退到真实屏幕尺寸；
GTK 屏幕 DPI 未设置（返回 -1）时，Cairo 采用默认字体缩放，避免负字号。
共享 wxcore 优先链接选中的内置 PNG/JPEG 实现，JPEG 编解码有真实往返回归。
wxrc 的相对 RUNPATH 支持下载后定位本包共享库；其帮助入口为 `--help`。
消费测试默认执行无显示 API 与共享状态回归；真机具有 GTK 显示连接时可用
`-c user.wxwidgets:gui_tests=True` 执行显示尺寸、窗口创建和 Cairo 字体回归。
