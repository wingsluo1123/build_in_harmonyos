# pd-boids — Pure Data 群集（boids）模拟

`boids` 是 Pure Data（Pd）的鸟群/兽群模拟外部对象（Eric Singer / A. Sier /
Jasch），基于 Craig Reynolds 的 Boids 算法，提供 `boids2d`（2D）与 `boids3d`
（3D）两个类。

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 在补丁中使用 [boids2d 10 0] / [boids3d 10 0]，bang 推进一帧
# 参数（neighbors/maxspeed/...）通过右 outlet 的 dump 消息读取
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
| `lib/pd-externals/boids2d.pd_linux` | 2D 群集模拟 |
| `lib/pd-externals/boids3d.pd_linux` | 3D 群集模拟 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |

## 参考资料

- 上游：<https://puredata.info>
- 许可证：GPL-2.0-or-later
