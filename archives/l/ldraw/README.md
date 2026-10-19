# ldraw

LDraw.org 官方零件库（LDraw Parts Library）——LEGO 零件的 LDraw 格式
几何数据（`.dat` 零件/基元）、颜色定义（`LDConfig.ldr`）、样例模型与许可文档。

本仓收录该零件库的 Conan 配方：把官方 `complete.zip` 完整库快照下载并
安装到 `share/ldraw/`（按 LDraw 生态惯例的库根路径），供 LDraw 兼容
渲染/查看类应用按标准库路径读取。

## 功能概述

- 提供 LEGO 零件的 LDraw 格式几何/颜色/基元数据（官方零件 3.4 万+）
- 上游以"按月滚动的完整库 zip + 日期版本号"发布（如 `20220211` = 2022-02-11 快照）
- 纯数据资源包：无编译步骤，无构建系统，无 CLI 产物

## OHOS 适配要点

| 项 | 说明 |
|---|---|
| 构建系统 | 无（纯数据包）。上游无 Makefile/CMake/meson/configure |
| 编译 | 不需要；`conan create` 只做"下载官方 zip → 解压 → 复制数据 → 消费侧校验" |
| 安装路径 | `share/ldraw/`（parts/、p/、models/、LDConfig*.ldr、许可文件） |
| 版本 | 与上游 LDraw 发布快照日期一致（20220211），配方 sha256 为本仓提交时实测官方制品哈希 |

## 版本

| 版本 | 说明 | 状态 |
|---|---|---|
| 20220211 | LDraw 官方零件库完整快照（历史权威指纹见版本级 notes.md） | built |

## 使用

```bash
conan install --requires=ldraw/20220211 -pr:h=ohos-aarch64
# 数据位于 <package_folder>/share/ldraw/（可用 LDRAW_LIB_PATH 环境变量定位）
```