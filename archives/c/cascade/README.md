# cascade

**RF 级联链路分析 —— 噪声系数、增益、三阶交调截点（IIP3）**

## 简介

cascade 读取一份描述射频接收链路（信号源 + 若干级放大器/滤波器/混频器/变压器）的文本文件，
逐级计算累计增益、累计噪声系数、IIP3、C/N 劣化与输出电平，并按各级对总噪声系数、
总 IIP3 的贡献排序。作者 Dan McMahill，SourceForge 项目 rfcascade，1.4 发布于 2001 年。

```
cascade ex1.cas
```

## 特性

- 整个程序是一个 `/bin/sh` 脚本，内嵌一段 awk 程序，无需编译
- 输入语法：`source c=-40 cn=25 bw=1e6`，随后每行 `<级名> g=<dB> nf=<dB> iip3=<dBm>`；
  支持 `gv=`/`gp=` 电压/功率增益、`rin=`/`rout=` 输入输出电阻、`defaults` 与 `@` 注释行
- 运行期依赖：`sh` 与 `awk`（上游要求 gawk/nawk/mawk，不支持老式 awk）

## 适配要点

- 上游是 autoconf 2.13 的 `configure` + `Makefile.in`，只做 `@awk@`/`@version@` 的 sed 替换；
  配方固定 `AWK=awk`，避免把构建机上探测到的 `mawk`/`gawk` 名字写进脚本
- 只构建 `cascade` 目标：默认 `all` 会用 `nroff -man` 预排版 cat1 手册页，OHOS CI 工具链没有 nroff；
  `cascade.1` 源页仍安装到 `share/man/man1`
- 补丁 `0001-cascade-drop-gawk-strftime.patch`：删除 `cascade.sh` 里仅 gawk 执行的 `strftime` 时间戳块。
  该块有 `ARGV[0]=="gawk"` 运行期保护，但没有 strftime 的 awk 在**解析阶段**就报 `Undefined function 'strftime'`，整个程序无法运行
- 无 Conan 依赖
