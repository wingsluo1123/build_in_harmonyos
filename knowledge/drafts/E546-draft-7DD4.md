# E546 — Imake/xmkmf 构建系统在 OHOS 不可用：老式 X11 软件的手工编译提取模式

## 错误现象

```text
./configure[69]: xmkmf: inaccessible or not found
make: *** No rule to make target 'Xaw3dP.h'.  Stop.
```

典型触发：源码树根目录有 `Imakefile`（或 `*.imake.conf`），上游 `configure`
脚本内部调用 `xmkmf -a` / `imake -I...` 生成 Makefile。OHOS 工具链不携带
imake 预处理器与 X11 config 规则树（`/usr/lib/X11/config/*.cf`），configure
在第一步就挂掉。

## 根因

Imake 体系（1990s—2000s 老式 X11 项目的构建标准，xpaint/xfig/xpdf/myman 等）
依赖：

1. `imake` 可执行文件（X11 开发工具，OHOS 无）；
2. `xmkmf` 包装脚本（X11R6 开发树，OHOS 无）；
3. `Imakefile` 经 C 预处理器展开成 `Makefile`，规则模板来自
   `/usr/lib/X11/config/` 下的 `.cf` 文件（OHOS 无）。

三者全部缺失 → 任何直接或间接调用 `xmkmf`/`imake` 的构建路径在 CI 必挂。

## 识别特征

- 源码树有 `Imakefile` 无 `configure.ac`/`Makefile.am`；
- configure 脚本内 grep 到 `xmkmf` 或 `imake`；
- 编译日志出现 `xmkmf: inaccessible or not found` 或
  `imake: No such file or directory`。

## 修复方案（推荐：手工编译单元提取）

**不碰 imake，绕开整个 Imake 体系**：

1. 通读 `Imakefile`，手工提取四要素：
   - `SRCS` / `OBJS`（编译单元清单，注意按 `#ifdef HavePNG` 等开关取
     **启用分支**的子集）；
   - `DEFINES`（含 `XAWLIB_DEFINES`、`-DSHAREDIR=` 等路径宏）；
   - `INCLUDES`（X11 头 + Xft/freetype2）；
   - `SYS_LIBRARIES`（链接清单，含内嵌静态库）。
2. 子目录 `Imakefile` 同样处理（xpaint 有三层：根 `Imakefile`、`rw/`、
   `xaw3dxft/`）。
3. 内嵌 vendored widget 库（如 xpaint 的 `xaw3dxft/`）随主程序编译为
   静态库 `libXaw3dxft.a` 一并链接——制品仓没有 libxaw3d/libxaw 包，
   内嵌自编译是唯一路径。
4. yacc/lex 生成物：xaw3dxft 的 `laygram.c/h`（yacc）与 `laylex.c`（lex）
   由 `.y`/`.l` 生成，CI 环境 flex 2.6.4 / bison 3.8.2 可用（`which flex`
   实证）；生成后需 `sed 's/yy/LayYY/g'` 前缀改写（Imakefile 原规则照抄）。
5. `Xaw3dP.h` 由 `Xaw3dP.h.sed` 经 sed 展开生成——纯 sed，无 imake 依赖。

### 预扫描

`prescan_pattern: \bxmkmf\b|imake -I|\.imake\.conf|Imakefile` 已注册——
适配前 `prescan` 命令扫到 Imakefile 即应预期走本条模式，选型阶段就按
"手工 Makefile"估算工作量。

## 禁止策略

- ❌ `apt install imake` / `xorg-dev`：CI worker 是 OHOS，无包管理器；
- ❌ 配方内调用 `xmkmf -a` / `imake -I`：工具不存在，configuration Hard Fail；
- ❌ 假设 `/usr/lib/X11/config` 存在。

## 关联条目

- E092（CMake 平台分支不识别 OHOS——同为老式构建系统的平台分派问题）
- P003（构建最少化原则）

## 实战案例

- xpaint 2.9.1.4（2026-10-05 适配）：三层 Imakefile 全部手工提取；
  内嵌 xaw3dxft 静态编译；依赖 libx11/libxt/libxext/libxmu/libxpm/libxft/
  freetype/libpng/zlib/libjpeg/libtiff（制品仓全部已发布）。
- myman 2009-10-30：上游无 Imakefile 但 configure 内含 xmkmf 探测分支，
  显式 `--x-includes/--x-libraries` 绕过（类似思路：不触发 imake 路径）。
