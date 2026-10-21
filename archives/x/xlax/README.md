# xlax

> X11 多窗口输入分发命令行工具（用 `SendEvent()` 把输入同时送进多个窗口）

## 简介

xlax 把用户在一个窗口里的键盘输入，通过 X11 的 `SendEvent()` 广播到若干个已经
选中的窗口，用于「多台机器 / 多个终端需要执行几乎相同操作」的场景。上游作者是
Frank Adelstein（2.0 版由 Thomas A. Fine 增加按 name hint 找窗口、改进 send
string、自动剔除已死窗口）。附带一个 Perl 助手 `mkxlax`（读 `~/.mkxlax` 配置
批量起窗口），安装为数据文件而不是可执行脚本。

本归档版本为 **2.4**，源码取自作者主页发布的 `xlax2.4.tar.gz`
（sha256 `aae925379d15ccec6fa9f82b14096d14613c9d342820e515aa61052bbe9ad2dc`，
与 Debian 打包所用的 `xlax_2.4.orig.tar.gz` 同一文件）。

## OHOS 适配要点

1. **构建系统**：上游是 1992 年的 Imake 工程（`xmkmf` + `make`），OHOS 无
   `imake`/`xmkmf`，因此配方绕过 Imake，直接用 profile 提供的 clang 15 编译唯一的
   翻译单元 `xlax.c`，头文件与库路径由当前 Conan 依赖图聚合（`build_system: custom`）。
2. **无 X server**：HarmonyOS PC 没有 X server，`XtAppInitialize()` 无法打开显示，
   所以 GUI 的「按键多路复用」行为在本平台无法端到端验证。补丁 0003 新增
   `--version` 与 `--selftest` 两个无头入口，`--selftest` 在 `XtAppInitialize()`
   之前执行，实际初始化 libXt、读取 libXaw 导出的 7 个 Athena widget class 记录、
   解析 `XmuClientWindow()`，共 12 项程序化检查；GUI 路径仍需在有 X server 的
   环境验证（见 `reports/test-report.md` §6）。
3. **不需要 libbsd**：Debian 的 `use-libbsd.diff` 是为了补 `strlcpy()`，而 OHOS 的
   libc 自带该函数，故本移植不引入 libbsd（ELF 的 `DT_NEEDED` 可证）。
4. **补丁来源与重生成**：三个补丁取自 Debian 打包的可移植性改动，但 Debian 的
   `fix-warnings.diff` 是在 `typos`、`use-libbsd` 之后生成的、行号带偏移，Conan 内置
   的 `patch_ng` 精确匹配行号会失配。因此用 GNU patch 按序应用得到结果树后，以
   `difflib` 逐文件重生成补丁，并做了 GNU patch / `patch_ng` 双通道复验。

## 依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| libxaw | 1.0.14 | Athena widget 集，提供 7 个 widget class 记录 |
| libxmu | 1.3.1.1 | `XmuClientWindow()`，由窗口反查顶层客户端窗口 |
| libxt | 1.3.1 | X Toolkit Intrinsics，初始化与应用上下文 |
| libx11 | 1.8.13 | Xlib，`SendEvent()`/`XQueryTree()` 等 |
| libxext | 6.4.0.1 | X11 扩展 |
| libxpm | 3.5.17 | 小图标/位图解析 |
| xorgproto | 2025.1 | X11 协议头 |

`XawClientLibs` 展开为 `Xaw Xmu Xt X11`，与上面的链接集合一致。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/xlax` | 主程序（ELF64 / AArch64 / PIE） |
| `share/man/man1/xlax.1`、`mkxlax.1` | 手册页 |
| `share/xlax/mkxlax`、`dot-mkxlax` | Perl 助手与样例配置（数据文件） |
| `licenses/LICENSE` | 上游版权声明 |
