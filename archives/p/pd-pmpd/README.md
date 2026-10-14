# pd-pmpd — Pure Data 物理建模外部对象库

`pmpd`（Physical Modelling for Pure Data，Cyrille Henry）是 Pure Data（Pd）的
一套物理建模外部对象，用于实时模拟质量-链接系统的物理行为：滚球、弦振动、
混沌、流体、沙堆、引力等。共 32 个类，含 `mass`/`mass2D`/`mass3D`、
`link`/`link2D`/`link3D`、`pmpd`/`pmpd2d`/`pmpd3d` 及信号版 `pmpd~` 等。

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 在补丁中使用 [mass]、[link]、[pmpd2d] 等
```

## OHOS 适配要点

- 上游使用 CMake 构建，每个类产出一个共享对象。
- `puredata/0.54.1`（application）**不暴露** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树，并把 `PUREDATA_INCLUDE_DIRS` 指向其 `src`。
- 上游默认对象名为 `.linux-arm64-32.so`，改用 `PUREDATA_SUFFIX=.pd_linux`，
  使 Pd 标准加载器可找到。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 32 个外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |

## 参考资料

- 上游：<https://github.com/ch-nry/pd-pmpd>
- 许可证：GPL-2.0-or-later
