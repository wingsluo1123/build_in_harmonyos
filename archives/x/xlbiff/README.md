# xlbiff

xlbiff 是经典 X11 biff 的现代维护版（edsantiago/xlbiff）：监视邮箱
spool 文件，发现新邮件时用 X Athena 组件弹出窗口显示
"from/subject" 摘要，支持 fade、键盘 LED、自定义 scanCommand 等。

- 上游：https://github.com/edsantiago/xlbiff
- 语言：C（mailbox-preview 辅助脚本为 Python）
- 构建系统：autotools（tag tarball 需 aclocal/automake 自举）
- 运行依赖：libX11 / libXt / libXaw / libXmu / libXrandr（conan 轨：
  libx11/1.8.13 force，对齐 libxaw/1.0.14）
- 产物：可执行文件 `bin/xlbiff` 与辅助脚本 `bin/mailbox-preview`
  （commands.json 已声明，R38）

## 4.6.11 适配要点

详见 `4.6.11/manifest.yaml` 与 `4.6.11/notes.md`：
autoreconf 直跑自举（HMDFS autoconf.m4f 冲突规避）、
--host=aarch64-linux 免 config.sub 补丁、E114 ac_tmp 重定向、
E182/E188 INSTALL shim。
