# fstobdf — OpenHarmony 预编译包

## 软件简介
fstobdf 是 X.Org 的字体服务器导出工具：通过 libFS 连接 X Font Server（FS 协议），
读取指定字体的信息与点阵位图，并在标准输出打印等价的 **BDF** 文件。它常用于
测试 font server、调试字体度量、以及从丢失的 BDF 源文件恢复字体。

与同族的 `fslsfonts`（只列字体名）不同，fstobdf 需要 **libFS + libX11** 两套客户端库：
`chars.c` 直接 include `X11/Xlib.h`，`configure.ac` 的
`PKG_CHECK_MODULES(FSTOBDF, [xproto >= 7.0.25 x11 libfs])` 同时要求 `xproto`、`x11`、`libfs`
三个 pkg-config 模块。

## 基本信息
- 软件名称: fstobdf
- 适配版本: 1.0.8
- 构建系统: autotools（上游 tarball 已内置生成的 `configure`）
- 目标平台: ohos-aarch64
- 源码地址: https://www.x.org/releases/individual/app/fstobdf-1.0.8.tar.xz
- 上游主页: https://gitlab.freedesktop.org/xorg/app/fstobdf
- 许可: MIT

## 使用方式
```bash
# 通过 conan 消费本配方（在 build_in_harmonyos 仓库内）
conan install --requires=fstobdf/1.0.8 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 产物为 bin/fstobdf 与 share/man/man1/fstobdf.1

fstobdf -version                     # 打印 'fstobdf 1.0.8' 并退出
fstobdf -server <host:port> -fn <font name> > out.bdf   # 导出字体为 BDF
FONTSERVER=<host:port> fstobdf -fn <font name> > out.bdf
```

## 可用版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.0.8 | built | HarmonyOS PC 上 `conan create` 通过，`test_package` 9 条无头断言全过（含 2 组负向对照实测）；主功能路径（导出字体）需可达的 X Font Server，运行期墙已如实披露（详见 1.0.8/notes.md） |

## 适配要点
- 补丁 0001：`config.guess` 补 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos`
  （E007；⛔ 不用 `--build/--host` 绕过，否则 autoconf 当交叉编译、产出错误 `config.h`）
- 补丁 0002：`configure` 两处 HMDFS 相关修改 ——
  ① `ac_pwd` 自检失败时回退 `$PWD`（首错 `configure: error: working directory cannot be determined`；E386 家族）；
  ② `config.status` 临时目录 `umask 077 + mktemp -d` → `umask 022 + mkdir + chmod 755`
  （700 目录在 HMDFS 上拒写，首错 `./confXXXXXX/subs1.awk: Permission denied`；E129/E110/E112）
- **只带两件补丁**（同族常见为三件）：本代 tarball 的 `config.sub` 实测已接受
  `aarch64-unknown-linux-ohos`（rc=0），故不带 `config.sub` 补丁
- pkg-config 视图：`PkgConfigDeps`（生成 `x11.pc`/`libfs.pc` 等，并把 xorgproto 的
  `share/pkgconfig` 一并暴露，使 `xproto`/`kbproto`/`fontsproto` 均可解析）+ `VirtualBuildEnv`
- 上游 C 源码零改动；两件补丁只动上游分发的 autotools shell 脚本，不含平台预处理器宏
- 未携带 install shim：本平台 `configure` 解析到 GNU `ginstall`，`ginstall -c` 对 man 页与
  二进制实测均成功（同族 appres 1.0.7 亦不带）。另：`$PWD` 兜底**已携带**（见补丁 0002 ①），
  它只对 HMDFS 的 cwd 失效做降级，CI 权威路径 `conan create` 并不需要它
- 无上游测试套件（`TESTS`/`check_PROGRAMS` 命中 0），测试全部由 `test_package` 自造：9 条真断言

