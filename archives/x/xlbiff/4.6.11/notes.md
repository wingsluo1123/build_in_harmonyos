# xlbiff 4.6.11 适配 notes（aarch64-linux-ohos / HarmonyOS PC）

上游：https://github.com/edsantiago/xlbiff（tag 4.6.11 tarball，
SHA256=b74e5d92466e82a63fe08be11a6f9a8f6b75ae5d0eb01fe6e46e89e60bbdddb9）
类型：X11 Athena GUI 应用（C，纯客户端，无内核/平台强绑定）→ 路径 A。
分支：feat/xlbiff-4.6.11。

## 1. 依赖图与轨道对齐

requires：libx11/1.8.13 (force)、libxext/6.4.0.1 (force)、libxt/1.3.1、
libxmu/1.3.1.1、libxaw/1.0.14、libxrandr/1.5.5、xorgproto/2025.1；
tool_requires：automake/1.18（conandata 无 configure/Makefile.in）。

- **轨道冲突 1**：libxrandr/1.5.5 配方 pin `libx11/6.4.0 (force=True)`，
  与 libxaw/libxt 轨（1.8.13）冲突 → 根配方 `libx11/1.8.13` force 胜出
  （conan override 语义，graph Overrides 输出
  `libx11/6.4.0: ['libx11/1.8.13']`），libxrandr 源码重建，实测定版。
- **轨道冲突 2（实测）**：libxrandr 还 pin `libxext/6.4.0`（非 force），
  与 libxmu/libxaw 轨的 6.4.0.1 冲突 → 根配方 `libxext/6.4.0.1
  force=True` 后图解析通过（首次 conan create 报
  "Conflict between libxext/6.4.0 and libxext/6.4.0.1"，加 force 修复）。
- libx11/1.8.13 轨使 libxpm/libxrender/libxrandr 源码重建（xaw 先例一致）。

## 2. 自举（bootstrap）

tag tarball 只有 configure.ac + Makefile.am。**不用 autoreconf**（HMDFS
上 autoconf.m4f 加载冲突，abiword-plugin-docbook E114 先例），按序直跑：

1. `${ACLOCAL:-aclocal}` --force（ACLOCAL 由 automake/1.18 buildenv 注入
   conanbuild；CI 沙箱 PATH 无 aclocal，必须走 env 引用）
2. `autoconf -o configure configure.ac`
3. autoheader 仅在 configure.ac 含 AC_CONFIG_HEADERS 时执行——xlbiff 没有
   （实测报 "autoheader: error: AC_CONFIG_HEADERS not found"，加条件跳过）
4. `${AUTOMAKE:-automake}` --add-missing --copy --foreign（生成 compile/
   install-sh/missing/depcomp）

## 3. configure（E114 修复链）

- `--host=aarch64-linux`：automake 1.18 自带 config.sub 可规范化
  （→ aarch64-unknown-linux-gnu），免 libxaw 式 config.sub 补丁；编译器由
  OHOS profile clang（--target=aarch64-linux-ohos）驱动。
- `--with-appdefaultdir=${datadir}/X11/app-defaults`：保持包前缀相对，
  DESTDIR 安装后可重定位。
- **E114**：config.status 在构建目录创建 confXXXXXX，安全框架拦子进程写。
  修法（adms/xeyes 同款）：预建固定可写 tmp 目录 → TMPDIR 内联注入
  configure 调用 → 用 sed 重写已生成 configure 的 `ac_tmp=$tmp` 为固定
  目录并中和相关 rm 陷阱。
- configure 必须以 `/system/bin/sh` 显式执行并 export
  SHELL/CONFIG_SHELL=/system/bin/sh（libxaw 先例）；脚本以绝对路径
  `<source>/configure` 调用（out-of-tree 构建目录下 `./configure` 不存在，
  实测 Error 127 后修正）。

## 4. E182/E188：make install 安装 shim

HMBS 的 install shim 只接受单文件双参调用，automake 批量
`install -c -m 644 f1 f2 dir/` 退出 64。沿用 adms 2.3.7 先例：构建期写
`_ohos_install_shim/install`（cp/mkdir 实现，chmod 容错跳过——HMFS 无
chmod 能力），sed 重写所有已生成 Makefile 的 `INSTALL = ...` 行指向
shim；INSTALL_DATA/INSTALL_PROGRAM 派生自 ${INSTALL} 自动跟随。
`make check` 无 TESTS（上游 Makefile.am 未定义），空操作。
安装走 `make install DESTDIR=...` + COPYING 复制，包内容含
bin/xlbiff、bin/mailbox-preview、两份 man1、XLbiff app-defaults、
etc/nmh/xlbiff.form。

## 5. test_package（R34/R51）

上游 tests/ 三个手动脚本需 nmh + X server，未接入 automake（discovered
3 / executed 0 / skipped 3，MANIFEST.yml 有逐项说明）。test_package 走
真实执行路径（coolmail/1.3 先例）：xlbiff 的 -version/-help 在
XtVaAppInitialize **之后**才处理（main() 第 226 行先开 display），无 X
server 时无任何参数路径能无头跑完，故校验：

1. 打包二进制存在可执行；
2. `strings | grep`（toybox 回退 grep -a）确认 4.6.11 版本串烧录；
3. 无 DISPLAY 运行退出码 1 且输出 "Can't open display:"——真实加载了
   libXaw→libXmu/libXpm→libXt→libSM/ICE→libX11→libxcb/Xau/Xdmcp→
   libXrandr/libXrender 全动态链并执行了 main() 前段；
4. 安装资源齐全（2 man、XLbiff、xlbiff.form、mailbox-preview）。

共 8 项检查，本地 conan test 实测 8/8 通过。
运行期 LD_PRELOAD 按依赖序注入依赖 .so 绝对路径（xeyes/1.3.1 的
stale_runtime_library 先例，OHOS loader 可能忽略 LD_LIBRARY_PATH）。

## 6. 本地验证记录（W3）

- conan create（-pr:h/-pr:b ohos-aarch64，--build=missing，
  --user=ohpcd --channel=stable）：17 包全绿，xlbiff 编译、安装、
  test_package 8/8 通过（reports/conan-create-log.md）。
- 过程问题（均已修复并留痕）：libxext 轨道冲突（加 force）；
  autoheader 无 AC_CONFIG_HEADERS（条件跳过）；./configure Error 127
  （绝对路径）；test_package 首版按 -version/rc0 设计但 xlbiff 需 display
  （改 coolmail 先例方案）。

## 7. 已知限制

- 真正的窗口/邮件扫描路径需要 X display + nmh，本环境无法执行
  （设备/CI 无 Xorg/Xvfb，多配方实证）；如需功能验证需在带 X server 的
  环境运行。
- 依赖 `ohpcd` 远程；libx11 轨 force 覆盖写在根配方，升级 libxrandr
  配方放开 pin 后可移除 force。
---

**编译结束**: 2026-10-17 07:53
**最终状态**: built
