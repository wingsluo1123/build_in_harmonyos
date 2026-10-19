# xfaces 3.3 适配笔记（aarch64-linux-ohos）

## 上游与源码

- xfaces 3.3，Christopher B. Liebman，1994-03-08 发布，MIT。
- 上游无存续官网；snapshot.debian.org 的 `xfaces_3.3.orig.tar.gz` 为**未修改**
  的上游原包（非 Debian 重打包/dfsg 改写）。ftp.x.org、ibiblio、funet 等
  historic 镜像逐一实测 404，snapshot.debian.org 为唯一可稳定获取的
  pristine 源（conandata.yml 已注明）。

## 构建系统规避（imake）

上游提供两套 Makefile，均不可用：

1. imake 生成的 Makefile：绑定 `sun.cf`/`/usr/X11R5`，imake 工具链 OHOS 无。
2. Makefile.noimake："for those without Imake"，但：
   - 绑定 `/usr/X11R5` 前缀与 netaudio `libaudio`（OHOS 无）；
   - 链接规则 bug：`$(TARGET)`/`$(LIBS)`/`$(IDIRS)` 未定义（实际变量名为
     `$(xfaces)`/`$(LIBS)` 定义不一致），直接 make 链接必失败。

**方案**：配方按 Makefile.noimake 的编译单元自写编译命令（myman/4.0.116
同款先例）：

- 编译单元 = 源码根 34 个 .c − `face_sound.c`（netaudio 后端，裁剪）
- 宏：`-DXPM -DSHAPE -DXFACE -DPOP -DLOOKUP_HOSTNAME`
- 链接：`-lXaw -lXmu -lXt -lXpm -lXext -lX11 -lcompface -lm`

## 依赖（W0 全部 conan download 实测已发布）

| 依赖 | 版本 | 用途 |
|---|---|---|
| libxaw | 1.0.14 | Xaw widget（传递 libxt/libxmu/libxpm/xorgproto） |
| libxext | 6.4.0.1 | shape.h（SHAPE 窗口异形） |
| libx11 | 6.4.0 | Xlib + 运行期 libxcb/libxau |
| compface | 1.5.2 | X-Face 头图像解码 |
| xorgproto | 2025.1 | 协议头 |

## 平台要点

- ELF 签名：package() 内 binary-sign-tool 自签（OHOS 拒绝未签名可执行）。
- /tmp 只读（E002）：source()/build() 钉 TMPDIR 到可写目录。
- 应用资源文件 XFaces.ad 安装到 share/xfaces/（Xt resource 默认加载路径
  不可写，仅随包分发）。

## 上游测试套件审计（R51）

- tarball 无 tests/ 目录、无 test/check 目标（Makefile.noimake 仅
  all/install/clean，grep 实证）→ 上游测试 0 项。
- test_package 以无效 DISPLAY 真实执行二进制：XtInitialize 打印
  "Can't open display" 后退出，先决条件是全部 X11/compface 动态符号解析
  成功 → 1/1 通过（100%，上游基线 0/0）。

## 状态

- 首次适配：3.3（R37 无后缀）。
---

**编译结束**: 2026-10-17 07:55
**最终状态**: built
