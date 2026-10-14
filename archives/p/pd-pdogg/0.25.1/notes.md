# pd-pdogg 0.25.1 适配笔记

## 上游构成

`pd-pdogg_0.25.1.orig.tar.gz` 是 Olaf Matthes 的 Pure Data Ogg/Vorbis 对象库
**pdogg**，提供 4 个类：`oggamp~`（Icecast2 流客户端）、`oggcast~`（流服务端）、
`oggread~`（文件读取）、`oggwrite~`（文件录制）。使用上游**老式 Pd library
template Makefile**，每个类产出一个 `<class>.pd_linux`。

## 构建

- **三方依赖**：`libvorbis/1.3.7`（制品仓现成，传递依赖 `libogg`）。上游 Makefile
  通过 `pkg-config --libs vorbis vorbisenc vorbisfile` 取 flag；配方改为从 Conan
  依赖图直接生成 `-I/-L/-l`，在命令行给出 `ALL_CFLAGS`/`ALL_LDFLAGS`/`ALL_LIBS`
  （命令行为最高优先级），无需 `pkg-config`。
- **Pd API 头**：制品仓 `puredata/0.54.1` 是 *application*，不暴露 `m_pd.h`；
  配方在 `source()` 额外拉取同版本 `pure-data 0.54-1` 源码树，`-I` 指向其 `src`
  （`oggread~`/`oggwrite~` 还包含 Pd 内部头 `s_stuff.h`，也在该 `src` 内）。
- **平台识别**：老式模板用 `uname -s` 判平台；OHOS 报 `HarmonyOS`
  → `make` 命令行强制 `UNAME=Linux`。
- 构建产出 **4** 个 `.pd_linux`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/oggamp~.pd_linux` | 流客户端 |
| `lib/pd-externals/oggcast~.pd_linux` | 流服务端 |
| `lib/pd-externals/oggread~.pd_linux` | 文件读取 |
| `lib/pd-externals/oggwrite~.pd_linux` | 文件录制 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |
| `lib/pd-externals/pdogg-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有帮助补丁）→ 上游 N=0。

消费者测试 `test_package/test_pd_pdogg.sh`（4 项断言）用**真机 OHOS `pd`** 无头
加载安装后的外部对象；4 个类在创建时各自 `post` 版本横幅，作为类已加载并实例化
的正向证据：

- `[oggamp~]` → `oggamp~: ogg/vorbis streaming client version 0.3`
- `[oggcast~]` → `oggcast~: ogg/vorbis streaming client version 0.2k`
- `[oggread~]` → `oggread~: ogg/vorbis file reader version 0.2c`
- `[oggwrite~]` → `oggwrite~: ogg/vorbis recorder version 0.1c`

真机 `conan create`：`CREATE_RC=0`，消费者 4/4。
