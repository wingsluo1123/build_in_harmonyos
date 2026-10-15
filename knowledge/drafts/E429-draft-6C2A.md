# GTK 后端连接成功后的几何与 DPI 能力校验（草稿）

日期：2026-10-12；实例：wxwidgets-gtk3/3.2.10.1，上游 wxWidgets 3.2.10。此条为路径 B 候选，正式编号、通用性与入库由官方审核。

## 现象与根因

设备的 GTK Broadway screen 为 1024×768，唯一 monitor 却返回 0×0，wx 默认窗口尺寸随之无效。另一个独立故障是 `gdk_screen_get_resolution()` 返回 -1.0（未设置），wxCairoContext 按 `resolution / 96` 缩放 11-point 字体，按比例可推导约 -117 Pango 单位，触发字号非负断言。连接/画布可见只证明显示通路，不能证明后端每项能力值有效。

## 输入、输出与修复

输入为真实 GDK screen/monitor/workarea、resolution、显示数量。输出为正的窗口/工作区尺寸及有效文字大小。0002 的 monitor geometry 到真实 GDK screen 尺寸回退，仅用于单监视器且 geometry 无效；无效 workarea 对任何 monitor 回退为该 monitor 的 GetGeometry；GetFromPoint 与修正后的 geometry 保持一致。0003 在 Cairo 上下文中对 resolution<=0 使用比例1，正DPI仍按原算法。

不硬编码屏幕尺寸，不伪造显示，不屏蔽 Pango 错误，不改上游断言。有效多监视器、正DPI为反例，不应进入回退；后端根本未连接时也不能靠该补丁补成显示能力。

## 验证证据与边界

受控 RED：GDK screen 1024×768、monitor0×0，wx geometry0×0；仅修几何时 GUI 回归仍失败，记录1次 Pango critical。GREEN：两补丁同时启用，wx geometry1024×768，GUI回归返回0、Pango errors=0。真实原版 minimal 示例窗口与 About 对话框另有截图记录。

本轮最终 Conan 包及 W3 结果另见本库 archives/w/wxwidgets-gtk3/3.2.10.1/reports/validation-summary.md，试验不得冒充已发布包。上游 GUI 仍存在后端窗口激活等失败；本知识仅覆盖上述两项能力值故障。测试源 test_wxgtk3_gui.cpp 保留 stderr 错误并创建真实 wxFrame、wxMemoryDC 和 Cairo context。

## 查重与增量

查重基线：main 63c58108a49fbe646911540cb64956b7cbeccd2f；检索 knowledge/graph、knowledge/doc、knowledge/drafts 的 `gdk_screen_get_resolution`、`PANGO_SIZE_NEGATIVE`、`monitor.*0x0` 无相同根因条目。E463/E527覆盖后端构建和工具，E471覆盖无显示时测试分类，DRAFT-headless-broadway-execute-upstream-gui-sample覆盖示例执行；均不覆盖已经连接后返回空几何/未设置DPI的数值边界及组合回归。相关已有条目继续引用，不申请其重复贡献。

推广对象包括 GTK GUI 绑定、兼容层和文本渲染。具体源码补丁仍依各库API契约调整；机器相似度结果与人工裁定见 reports/knowledge-review.md。
