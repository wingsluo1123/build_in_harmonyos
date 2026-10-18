# XShogi

> GNU Shogi（日本将棋）引擎的 X11/Athena（Xt/Xaw）图形前端。

## 简介

XShogi 是 GNU Shogi（`gnushogi`，日本将棋引擎）的图形前端，用 X11 Athena
widget（Xt/Xaw）绘制棋盘，对接 gnushogi 引擎进行本地或远程对弈。它是一个纯
可执行程序（无库、无对外头文件），消费者视角唯一真实的用法就是运行安装后的
`bin/xshogi`。

本仓库提供其在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## OHOS 适配要点

- **AC_PATH_XTRA 探测跳过**：CI 与真机均无 `xmkmf`、无系统 X11 树，`configure`
  的 X 探测会走 Imakefile 分支。配方在 `generate()` 经
  `AutotoolsToolchain.environment()` 预置 autoconf 缓存变量
  `ac_cv_have_x="have_x=yes"` 整段跳过探测，X 头/库路径全部由 `AutotoolsDeps`
  注入的 `CPPFLAGS/LDFLAGS/LIBS` 提供（不写死系统前缀）。
- **无头 `-version` 补丁**：libXt 1.3.1 的选项表没有 `-help/-version`，上游
  `main()` 在 `XtAppInitialize` 之前不判 argc，任何调用都会先撞 `XOpenDisplay`。
  补丁 `0001-add-version-option.patch`（纯追加、无平台宏）在 `XtAppInitialize`
  之前对 `-version`/`--version` 打印版本并 `exit(0)`，使无头下拉取版本（CI L2
  smoke）可行；同款约定见 xeyes/appres 上游。
- **运行期自包含**：设备无系统 X11 运行期库（实测 `/lib`、`/lib64`、`/usr/lib`、
  `/system/lib*`、`$HOME/usr/local/lib` 均无 `libX11*`/`libXaw*`）。配方
  `package()` 把依赖的 117 个 `.so` 复制进包内 `lib/`，二进制链接期
  `DT_RPATH=$ORIGIN/../lib`（`readelf -d bin/xshogi` 实测），裸环境
  `bin/xshogi --version` 即可 rc=0。`lib/` 不通过 `cpp_info.libdirs` 对外暴露
  （应用包，非链接接口）。

## 排除与替代

不适用（本包只安装 `bin/xshogi` 单个可执行文件，无子命令/组件替代关系）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| xorgproto | 2025.1 | X11 协议头 |
| libx11 | 1.8.13（override） | libX11.so.6，Xlib |
| libxext | 6.4.0.1 | libXext.so.6（上游 `-lXext`） |
| libxt | 1.3.1 | libXt.so.6，`XtAppInitialize` |
| libxmu | 1.3.1.1 | libXmu.so.6 |
| libxaw | 1.0.14 | libXaw.so.7，Athena widget |

传递依赖（Conan 自动解析，ohpcd 均有 OHOS/armv8 二进制）：libxpm、libsm、
libice、libxcb、libxau、libxdmcp、xtrans、xcb-proto。

## 功能验证

```bash
# 版本（不需要 X server）
bin/xshogi --version     # → xshogi version 1.4.2 based on xboard version 2.0/2.1
bin/xshogi -version      # 单横线形式同

# 完整 GUI 需真实 X server（设备/CI 为无头，未验证）
DISPLAY=:0 bin/xshogi
```

`test_package` 的消费者测试真实执行包内二进制 3 条断言：`--version`、`-version`
（均断言退出码 0 + 版本串），以及无效 `DISPLAY` 下 `-help`（断言非 0 退出且报
Xt 显示失败诊断，证明二进制真加载 X11/Xt 并调用 `XtAppInitialize`）。

## 平台限制与未验证项

- **GUI 功能未在设备验证**：设备无 X server，棋盘绘制、菜单交互、与 gnushogi
  引擎的本地/远程对局**均未验证**；门禁只覆盖"二进制真实执行 + X11/Xt 链接路径
  可达"（无效 DISPLAY 下的 Xt 显示失败诊断）。
- **conan-verify 的 L2/L4/L5 被 skip**（工具侧 G4 无法解析带 `@user/channel` 的
  ref），这三闸由 CI 同构 `build_and_test.sh` 实际执行并通过（CI L2
  `xshogi --version OK`）。
- 上游 xshogi 1.4.2 无自动化测试套件（N=0/N′=0），清点证据见
  `1.4.2/test_package/MANIFEST.yml` 的 `upstream_test_audit`。

## 参考

- [官方主页](https://www.gnu.org/software/gnushogi/)
- [源码 tarball](https://ftp.gnu.org/gnu/gnushogi/xshogi-1.4.2.tar.gz)
- 配方、补丁与适配笔记见 `1.4.2/`
