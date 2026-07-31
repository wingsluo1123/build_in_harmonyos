# lite (Lite XL)

Lite XL 是一个用 Lua + C 编写的轻量、快速、开源的文本编辑器，致力于在保留
高效编辑体验的同时提供极低的内存占用与流畅响应。它是知名编辑器 lite 的社区
活跃分支（上游项目：https://github.com/lite-xl/lite-xl）。

## 功能概述

- 轻量快速：核心用 C 编写，启动与响应速度快
- 可扩展：内嵌 Lua 5.4 运行时，插件与配置全部用 Lua 编写
- 现代化界面：基于 SDL2/SDL3 + FreeType2 渲染，支持 GPU 加速
- 跨平台：Linux / macOS / Windows / BSD / 鸿蒙（本适配目标）

## 构建信息

| 项 | 值 |
|----|-----|
| 版本 | 2.1.8 |
| 构建系统 | meson |
| 许可证 | MIT |
| 产物 | `bin/lite-xl`（GUI 应用）+ `share/lite-xl/`（运行时数据） |
| 包类型 | application（R38：软件级 `commands.json` 已声明） |

## 依赖

- sdl2/2.30.10（上游优先 SDL3；本仓 sdl3/3.4.8 仅有 OHOS 适配归档、**无 conan 配方**，暂用 SDL2，SDK3 切换路径见 `2.1.8/notes.md`）
- freetype/2.14.3
- lua/5.4.8
- pcre2/10.45.1
- agg —— **W0/R36 阻塞**：本仓暂无 agg 配方，需先适配并发布 agg 包再构建本包

## OHOS 适配要点

- Meson + PkgConfigDeps：依赖全走 conan，`wrap_mode=nodownload` 禁止 meson 网络下载子项目
- OHOS 下 meson 需注入 ar/ranlib 全路径到 `conan_meson_native.ini`
- 产物可执行文件需 `binary-sign-tool` 签名（OHOS XPM 要求）
- 详细适配过程见 `2.1.8/notes.md`

## 验证状态

- 2.1.8：配方静态生成完毕；`conan create` / sha256 / W0 依赖发布验证
  因沙箱无法 spawn shell 而**环境阻塞**，待真实环境执行（未伪造验证结果）。
