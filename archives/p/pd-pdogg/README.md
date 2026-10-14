# pd-pdogg — Pure Data Ogg/Vorbis 对象库

`pdogg`（Olaf Matthes）为 Pure Data（Pd）提供 Ogg/Vorbis 支持，包含 4 个对象：

- `oggamp~` — Icecast2 等 Ogg/Vorbis 流客户端
- `oggcast~` — Ogg/Vorbis 流服务端
- `oggread~` — Ogg/Vorbis 文件读取
- `oggwrite~` — Ogg/Vorbis 文件录制

## 依赖

- `libvorbis/1.3.7`（制品仓，传递依赖 `libogg`）

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 在补丁中使用 [oggread~]、[oggwrite~] 等
```

## OHOS 适配要点

- 上游使用**老式 Pd library template Makefile**，每个类产出一个 `<class>.pd_linux`。
- 上游通过 `pkg-config` 取 vorbis flag；配方改为从 Conan 依赖图生成并在命令行给出
  `ALL_CFLAGS`/`ALL_LDFLAGS`/`ALL_LIBS`。
- `puredata/0.54.1`（application）**不暴露** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树（含 `s_stuff.h`），并把 `-I` 指向其 `src`。
- 模板用 `uname -s` 判平台；OHOS 报 `HarmonyOS`，故在命令行强制 `UNAME=Linux`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/oggamp~.pd_linux` | 流客户端 |
| `lib/pd-externals/oggcast~.pd_linux` | 流服务端 |
| `lib/pd-externals/oggread~.pd_linux` | 文件读取 |
| `lib/pd-externals/oggwrite~.pd_linux` | 文件录制 |

## 参考资料

- 上游：<https://puredata.info>
- 许可证：LGPL-2.1-or-later
