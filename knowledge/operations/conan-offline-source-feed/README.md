# Conan 离线源喂包：backup source 配对与 URL scheme 一类共性问题

> 知识库拓展条目（解决的是一类共性问题，不是单个库的补丁）。
> 适用对象：任何在网络受限环境（离线设备/内网构建机/CI clean 环境）做 `conan create` 的三方库适配——只要 `source()` 需要从上游 URL 拉源码包，都可能命中本条。
> 交付物：本文档 + 检测脚本 `detect-conan-offline-source.sh` + 样例演示库 `sample/`（japa 0.9.4 实测）。

## 1. 问题定位

Conan 2 的 **backup sources** 机制（`core.sources:download_urls`）与 **download cache**（`core.sources:download_cache`）在离线/弱网环境是标准绕坑手段，但有三条共性陷阱，任何一条命中都会让 `source()` 阶段直接失败：

| # | 陷阱 | 根因 | 报错特征 |
|---|------|------|---------|
| 1 | backup 源只放了 `<sha256>` 文件，没放 `<sha256>.json` | `caching_file_downloader.py` 要求 sha256 包与元数据 **成对下载**：`download(backup_url + sha256)` 后必须再 `download(backup_url + sha256 + ".json")`，缺 json 整体按 NotFoundException 判负 | `Sources for <URL> not found in remote backup <base>` |
| 2 | `download_urls` 用 `file:///<dir>` | 本机 conan 2.29.1 底层 requests 对 `file://` **没有 connection adapter**（`No connection adapters were found`）；裸路径 `/dir` 则报 `No scheme supplied` | `No connection adapters were found for 'file://...'` |
| 3 | 残留上一次任务的 `global.conf` 临时配置 | TEMP 注释的 `download_urls`/`download_cache` 是会话级临时改动，任务结束忘还原 → 下一个任务的 source() 被指向死端口/旧目录 | `not found in remote backup http://127.0.0.1:<旧端口>/` |

关键点：backup 源的查找键是**文件内容 sha256**（不是 URL sha256、不是文件名）；conan 请求的路径是 `<base>/<sha256>` 与 `<base>/<sha256>.json`（conan 源码 `conan/internal/rest/caching_file_downloader.py:104-107`）。

## 2. 典型报错特征（error_signature）

- `NotFoundException: Sources for <URL> not found in remote backup <base>`
- `No connection adapters were found for 'file://...'`
- `No scheme supplied`（download_urls 写裸路径）
- `ConanException: Error downloading file <base>/<sha256>`

三条同时或先后出现时，几乎必然是「backup 源配置不完整/失效」而非上游 URL 本身不可达——先核对 backup 源，再怀疑网络。

## 3. 检测脚本

```bash
bash knowledge/operations/conan-offline-source-feed/detect-conan-offline-source.sh \
    [--conf <global.conf 路径>] [--log <conan 日志文件>...] [--json]
```

做三件事：

1. **配置扫描**：读 `~/.conan2/global.conf`（或 `--conf` 覆盖），解析 `core.sources:download_urls` / `download_cache`：scheme 是否被 conan 支持（仅 http/https，`file://`/裸路径报 blocker）；URL 是否可达（HEAD 探测）；TEMP 残留标记检测（warn）。
2. **sha256 成对完整性**：对配置的每个 backup base，若能解析出本地目录/HTTP 目录，逐个校验 `<sha256>` 文件是否有配套 `<sha256>.json`（缺 json 报 blocker，含修复建议）。
3. **日志匹配**：对给定 conan 日志匹配 §2 的四条 error_signature，命中则输出命中行 + 定级 + 策略。

退出码契约：

| 码 | 含义 |
|---|---|
| `0` | 无 blocker（warn 不阻断） |
| `2` | 用法错误 |
| `10` | 存在 blocker —— 可直接当预检闸用 |

## 4. 处理策略（可组合）

1. **HTTP 喂源（推荐）**：在源码包目录起本地 http.server，目录内同时放：
   - `<内容sha256>` —— 源码包本体；
   - `<内容sha256>.json` —— 元数据 `{"references": {"<pkg>/<ver>": ["<官方URL>"]}, "timestamp": <epoch>}`（照抄 dl-cache 既有 json 结构）。
   然后 `core.sources:download_urls=["http://127.0.0.1:<port>/"]`。`file://` 与裸路径在 conan 2.29.1 上不可用。
2. **download_cache 预置**：把 `<内容sha256>` + `.json` 直接放进 `download_cache` 目录——conan 命中本地缓存后跳过 backup 远端（注意：缓存命中分支也会校验 json 元数据）。
3. **配置卫生**：TEMP 配置用后必须还原 `global.conf`；换端口/换目录时同步改 `download_urls`，避免下一个任务踩残留配置（陷阱 #3）。sha256 用 `sha256sum <tarball>` 取，重命名后必须与文件内容一致。

## 5. 样例演示库：japa 0.9.4（实测）

样例与复现脚本见 `sample/`：

- `sample/repro.sh` —— 复现脚本（日志重定向到文件，规避 SIGPIPE，不用管道 head）：
  - **不启用本方案**：`download_urls=["file:///..."]`（或 backup 缺 json）→ `conan create` 在 source() 失败，复现 `No connection adapters` / `not found in remote backup` 报错；
  - **启用本方案**：`download_urls=["http://127.0.0.1:8732/"]` + 成对 sha256/json → `conan create` 全流程通过（japa 实测 RC=0，`JAPA_SMOKE_PASS load=2 process=1 skipped=3 failed=0`）。
- `sample/evidence.md` —— japa 实测的报错原文、修复命令、前后对照（create2/create3/create4 失败 → create5 通过）。

## 6. 边界与不适用场景

- **网络可达上游时无需本条**：backup sources 只是弱网绕坑，上游直连成功时 conan 不走 backup 分支。
- **CI 环境**：CI worker 有正常网络与官方镜像 fallback，本条主要用于本地/离线设备/内网构建机。
- **不解决 sha256 校验失败**：若包内容与 conandata.yml 声明的 sha256 不一致，属另一个问题（配方侧 sha256 错误），本条的喂源方案无法掩盖它——conan 仍会校验并报 sha mismatch。
- **conan 版本差异**：sha256+json 成对行为以 conan 2.29.1 源码为准（本仓库基线），升级 conan 后需复核 `caching_file_downloader.py`。
