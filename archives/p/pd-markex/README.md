# pd-markex — Pure Data 外部对象集合（Mark Danks）

`markex` 是 Mark Danks 的经典 Pure Data（Pd）外部对象集合，共 20 个类：
数学/序列（`average`/`counter`/`alternate`/`oneshot`/`tripleRand`/`tripleLine`/
`randomF`）、颜色空间（`hsv2rgb`/`rgb2hsv`）、向量运算（`vector+`/`vector-`/
`vectorabs`/`vectorpack`/`vector0x2a`/`vector0x2f`）、信号（`abs~`/`reson~`/
`invert`）、字符串（`strcat`）等。

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 在补丁中直接使用 [average]、[rgb2hsv]、[strcat] 等
```

## OHOS 适配要点

- 上游使用**老式 Pd library template Makefile**（非 pd-lib-builder），每个类产出一个
  `<class>.pd_linux`。
- `puredata/0.54.1`（application）**不暴露** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树，并把 `-I` 指向其 `src`。
- 模板用 `uname -s` 判平台；OHOS 报 `HarmonyOS`，故在命令行强制 `UNAME=Linux`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 20 个外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |

## 参考资料

- 上游：<https://puredata.info>
- 许可证：GPL-2.0-or-later
