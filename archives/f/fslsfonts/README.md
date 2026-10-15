# fslsfonts — OpenHarmony 预编译包

## 软件简介
fslsfonts 是 X.Org 的 X 字体服务器（Font Server，FS 协议）客户端：通过 libFS
连接 font server，按模式列出其上可用的字体名称，并可显示每个字体的长信息、
属性、字符 min/max 边界等。它是纯 FS 协议客户端，不依赖 X server / libX11。

## 基本信息
- 软件名称: fslsfonts
- 适配版本: 1.0.7
- 构建系统: autotools（上游 tarball 已内置生成的 `configure`）
- 目标平台: ohos-aarch64
- 源码地址: https://xorg.freedesktop.org/archive/individual/app/fslsfonts-1.0.7.tar.xz
- 上游主页: https://gitlab.freedesktop.org/xorg/app/fslsfonts
- 许可: MIT

## 使用方式
```bash
# 通过 conan 消费本配方（在 build_in_harmonyos 仓库内）
conan install --requires=fslsfonts/1.0.7@ -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 产物为 bin/fslsfonts
fslsfonts -version
fslsfonts -help
FONTSERVER=<host:port> fslsfonts -l        # 列出字体（需可达的 font server）
fslsfonts -s <host:port> -l -m             # 指定服务器并显示 min/max 边界
```

## 可用版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.0.7 | built | HarmonyOS PC 上 `conan create` 通过，`test_package` 6 条无头断言全过；主功能路径（列出字体）需可达的 X font server，运行期墙已如实披露（详见 1.0.7/notes.md） |

## 适配要点
- `config.guess` / `config.sub` 补丁识别 HarmonyOS 与 `ohos` 三元组（不写死
  `--build/--host`，`config.log` 中 `host='aarch64-unknown-linux-ohos'` 即补丁真实生效的证据）
- HMDFS 补丁：`configure` 在 `pwd`（`getcwd`）失败时回退 `$PWD`，`config.status` 临时目录
  `umask 077 → 022`
- pkg-config 视图：`PkgConfigDeps`（libfs.pc + xproto.pc）+ `VirtualBuildEnv`，
  依赖只需 `libfs/1.0.10` + `xorgproto/2025.1`
- OHOS 下把 Makefile 的 `INSTALL` 重定向到 cp/mkdir shim（HMFS 上带 `-c` 的 install 会失败）
