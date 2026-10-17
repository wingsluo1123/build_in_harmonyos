# uqm — The Ur-Quan Masters

## 简介

The Ur-Quan Masters（UQM）是 1992 年 DOS 游戏 **Star Control II** 的开源复刻版，
由 Toys for Bob 原始素材 + 社区重写的可移植引擎构成。核心玩法包括星际探索、
资源采集、舰船改装与实时太空战斗（Supermelee），支持双人网络对战。

- 官网: http://sc2.sourceforge.net/
- 源码: https://sourceforge.net/projects/sc2/files/UQM/
- 许可证: GPL-2.0-or-later

## OHOS 适配

- **构建系统**: 上游自研 `./build.sh uqm`（非 autotools/cmake/meson），
  configure 为交互式文本菜单 → 配方合成 `config.state` 走 `reprocess_config` 无人工配置
- **图形/音频**: SDL2（静态）为渲染与输入后端；音频走 MixSDL → OHOS `ohaudio`
  （实测 44.1 kHz / 16 bit / stereo 正常初始化）
- **依赖**: sdl2 / libpng / libvorbis / zlib（全部制品仓预编译包）；
  Tracker 音乐使用源码内置 libmikmod，不引入外部 libmikmod
- **补丁**: 2 个可移植性补丁（`$TMPDIR` 临时目录、musl `<sys/select.h>`），
  均为纯 POSIX 写法，不含平台宏

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.8.0 | built | 首次适配；conan-verify G0-G4 + L2/L4/L5 通过，test_package 4/4 |

## 使用

```bash
conan install --requires=uqm/0.8.0
uqm --version        # 0.8.0
uqm --help           # 选项表
```

> ⚠️ 游戏**内容包**（`uqm-0.8.0-content.uqm` 等）是上游单独发布的资源，不随本包
> 安装；需自行下载后放入 `share/uqm/content/packages/`，或通过 `--contentdir` 指定
> 内容目录后才能开始游戏。本包提供的是可运行的程序本体。
