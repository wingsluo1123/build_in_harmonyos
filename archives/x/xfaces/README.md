# xfaces — X11 faces/mail 监视器

xfaces 是 Christopher B. Liebman 于 1994 年发布的 X11 应用：周期性检查
系统邮箱（本地 spool 或 POP3），在桌面上以图像网格（faces 邮政图像库、
X-Face 头、XBM/XPM 图像）显示邮件收件人/发件人列表，支持声音通知
（netaudio，本适配裁剪）、邮件注记、正则驱动的发件人搜索等。

- 上游：1994-03-08 发布 3.3（无官方站点存续，tarball 由
  snapshot.debian.org 以未修改的 .orig.tar.gz 归档）
- 许可证：MIT（COPYRIGHT）
- 构建系统：imake / Makefile.noimake（均不可直接用于 OHOS，配方内自写
  编译命令，见 3.3/conanfile.py 与 3.3/notes.md）
- 上游可选特性启用情况（本适配）：XPM ✓ SHAPE ✓ XFACE(compface) ✓
  POP3 ✓（内建，无外部依赖）；netaudio 声音 ✗（OHOS 无 libaudio，裁剪）

## 目录

- 3.3/ — 首次适配（aarch64-linux-ohos）
