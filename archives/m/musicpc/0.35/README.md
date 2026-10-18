# musicpc 0.35 — HarmonyOS PC 构建归档

- 软件：musicpc（mpc，MPD 最小化命令行客户端；「musicpc」是 FreeBSD ports 树对 mpc 客户端的命名，上游工程 MusicPlayerDaemon/mpc，v0.35 发布于 2023-12-21）
- 版本：0.35
- 构建系统：meson
- 语言：C（src/ 下 .c + .h，c_std=c99）
- 许可证：GPL-2.0-or-later
- 上游主页：<https://www.musicpd.org/clients/mpc/>
- 源码包：<https://www.musicpd.org/download/mpc/0/mpc-0.35.tar.xz>
  （sha256 `382959c3bfa2765b5346232438650491b822a16607ff5699178aa1386e3878d4`，49820 字节；
  上游官方站 https 直链，实测 HTTP 200）
- 依赖：`libmpdclient/2.23`（**plain name/version 形态**，ohpcd 制品仓已发布，
  上游 meson 要求 `>= 2.18`；`@ohpcd/stable` 形态在本仓实测不可解析——
  见 `archives/m/mpdas/0.4.5/notes.md`）
- 与 `mpc/1.3.1`（GNU MPC 数学库）**无关**，同名不同软件

## 构建

```bash
conan create archives/m/musicpc/0.35 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方经 PkgConfigDeps 从 conan 依赖图解析 libmpdclient（meson
`dependency('libmpdclient', version: '>= 2.18')` 走 pkg-config）；
`wrap_mode=nodownload` 防止 meson 回退到包内 `subprojects/` 的 wrap 文件
（上游自带 libmpdclient.wrap）；`documentation=disabled` 跳过 sphinx
（manpage 是 sphinx 生成物，本构建不打包）；`test=false`（上游单测依赖
`check` 库且仅能原生运行，交叉编译下不满足，见 notes.md 测试账）。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/mpc` | 可执行文件（aarch64 ELF） |
| `share/doc/mpc/` | 上游 AUTHORS / COPYING / NEWS / README.rst 与 contrib 脚本 |

## 运行

```bash
mpc status                       # 连接 MPD（$MPD_HOST / $MPD_PORT 或 -H/-P 指定）
mpc -H host -P 6600 status
mpc help                         # 命令列表（无需服务器）
```

详细适配过程与限制见 `notes.md`。
