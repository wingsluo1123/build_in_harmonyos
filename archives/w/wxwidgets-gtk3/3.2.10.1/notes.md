# wxwidgets-gtk3 3.2.10.1 共享修订

上游wxWidgets3.2.10。R37新增修复版本，已发布3.2.10配方未改。默认shared共享exe/SDK/plugin的wxApp，explicit static可配置但本轮无其新版本真机通过声明。

## 实际修复

0001沿用OHOS平台识别；socket fallback用socklen_t保留网络API。0002修唯一monitor空geometry，无效workarea回退其monitor geometry；0003未设置DPI用默认比例，保持有效DPI和多monitor行为。0004修shared系统codec先满足符号导致JPEG90/62 ABI不一致，真实往返RED1/GREEN0及最终消费者通过。wx-config解析当前前缀，wxrc相对symlink及$ORIGIN RUNPATH；安装后14 ELF最终路径原地签名。GUI日志回归仅用GLib API，直接glib/2.84.0.1避免无关GTK头缺hb.h，断言未降低。

## 上游测试申报

test301、test_gui354、drawing1、allheaders1=657注册组；11预期编译失败另计，总668。636通过、29失败、FTP1跳过、人工2未跑，实际665项通过率95.64%。4正控源先编译成功。原版条件跳过另列warnings，不伪报全分支覆盖。858仅CPPUNIT方法/SECTION，旧295静态执行不沿用。

3/3消费者、16检查点通过，真机GUI零Pango critical。原始W3 L0/L1/L2/L4/L5逐项pass、反向依赖检查通过。ConanVerifier PASS但G4缓存解析skip，真实Conan cache path补充原L2/L4/L5及SDK13 ELF检查通过。legacy staging1/3 --version，wxrc不支持该参数但--help通过，完整工具留在Conan包。

## 知识与边界

使用E092、E463/E471/E527和已有SONAME/RUNPATH/签名知识。新增6C2A（已连接后端能力值仍无效）、6C2B（shared包装库builtin codec链接选择及ABI证据链），成对草稿在knowledge/drafts，工具查重create建议、schema检查有原报告；不是官方入库/已获10分。

上游失败逐项保留reports/validation-summary.md。GTK schema、字体/图标、窗口管理和GNU ls前提明示；可选TIFF/OpenGL/media/webview关闭。Broadway不是原生桌面后端。本次不改框架/正式图谱/3.2.10源码、不自动合并。CodeBlocks按R36等共享制品发布后重新W0并验证IDE/插件。PR、当前HEAD远端CI、审核、合并和发布分别记录。

## 对话记录

### 对话 #1

- 用户要求按鸿蒙三方适配流程继续CodeBlocks；共享wx依赖不存在时明确回复“暂无，按流程处理缺失依赖”。
- 用户授权设备通过全局SSH入口使用，后续不依赖USB。
- 路径B申请身份经API核验；用户明确队伍名称为“天天开心”。

归档工具finalize的legacy release/debug目录布局与Conan cache save归档不同：只有真实Release构建，无Debug构建或虚构debug包；此布局警告如实保留，submission的实际缓存归档存在性检查另核验。
---

**编译结束**: 2026-10-13 00:40
**最终状态**: built
