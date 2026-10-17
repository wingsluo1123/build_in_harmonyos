# DRAFT: conandata.yml 单元素列表形态静默跳过 CI mirror fallback 注入——worker 无 curl + 官方源不可达时 source() 裸连超时

> 配套条目：`DRAFT-apt-pkg-2.7.14-conandata-single-element-list-ci-mirror-skip.kv`（本 md 与 kv 成对）
> 状态：pending-editor-review（拟提升编号 E7xx，最终由主编确认）
> 首发实现：apt-pkg 2.7.14，PR #14901，CI #85897
> 同族先例：E549（boost1.84-program_options 双 URL 列表）、DRAFT-ci-predl（keditbookmarks 等六件 PR worker 无 curl）

## 1. 错误特征（可机器匹配）

```
[step] Pre-download: extracting source URLs from conandata.yml...
  [try 1/2.1/3] 2.7.14.tar.gz ← https://gh-proxy.com/https://github.com/Debian/apt/archive/refs/tags/2.7.14.tar....
  [fail] [Errno 2] No such file or directory: 'curl'
  [try 2/2.1/3] 2.7.14.tar.gz ← https://github.com/Debian/apt/archive/refs/tags/2.7.14.tar.gz...
  [fail] [Errno 2] No such file or directory: 'curl'
  [WARN] Failed to pre-download 2.7.14.tar.gz, will rely on conan's download
  [done] No files pre-downloaded
...
apt-pkg/2.7.14: Calling source() in /storage/Users/currentUser/.cache/conan2/p/apt-*/s
ERROR: Error in source() method: Error downloading file
https://github.com/Debian/apt/archive/refs/tags/2.7.14.tar.gz:
'HTTPSConnectionPool(host='github.com', port=443): Max retries exceeded
(Caused by ConnectTimeoutError(...'Connection to github.com timed out. (connect timeout=30)'))'
[fail] apt-pkg/2.7.14 — conan create failed
```

- error_signature：`\[fail\] \[Errno 2\] No such file or directory: 'curl'|\[WARN\] Failed to pre-download .*, will rely on conan's download|Error in source\(\) method.*Error downloading file https://github\.com/.*connect timeout=30`
- **识别要点**：CI 失败诊断自动归为"网络问题/源码下载超时"（提示"已知可达: zlib.net; 已知不可达: ftp.gnu.org"）——极具误导性。真因是 **conandata.yml 的 URL 形态**（单元素列表 → CI 镜像注入被静默跳过）+ 环境双因子（worker 无 curl + 官方 host 不可达），不是"换个可达的源"能解决的。

## 2. 根因

`ci/conan/build_and_test.sh` 的 Mirror fallback 段（L1018-1058）入口条件是**单行正则**：

```bash
grep -qE 'url:.*https://(archives\.boost\.io|github\.com|...)/' "$CONANDATA"
```

它要求 `url:` 与 `https://已知域名/` 出现在**同一行**。ohc-run.py conan-init 自动生成的 conandata.yml 把 `sources.url` 写成**列表形态**（`url:` 后换行、URL 以 `- ` 为条目前缀）——即使只有一条 URL：

```yaml
# conan-init 默认产出（单元素列表形态——CI 镜像注入被静默跳过）：
sources:
  url:
    - "https://github.com/Debian/apt/archive/refs/tags/2.7.14.tar.gz"
```

`url:` 与 URL 不同行 → 正则不命中 → CI **静默跳过镜像改写**（无任何提示），conan source() 只能裸连官方 host。叠加两个环境因子：

1. **worker 无 curl**（pre-download 段 `[Errno 2] No such file or directory: 'curl'` ×3，镜像预拉也被掐断，只 WARN 降级不阻断）；
2. **官方 host 在 CI worker 上 TCP 不可达**（github.com ConnectTimeout 30s）。

两个因子同时存在时 conan get() 只剩官方 URL 一条路 → 超时 → conan create 失败。与配方质量无关：**同一 PR 撞到有 curl 且 github 可达的 worker 就绿，撞到无 curl + 网络受限的就红**——随机红绿的又一个来源。

**apt-pkg 特有教训**：commit 8fb99bd2 曾把列表里的 gh-proxy.com 镜像项删除（"restore official source URL"），但**残留了列表形态**——恰好把 CI 自动注入也关掉了，比删前（gh-proxy 显式在列表里，conan 多源尝试）更脆弱。

## 3. 解法（配方侧自愈：改回单值官方 URL）

conandata.yml 的 `sources.url` 改回**单值官方 URL 字符串**（url: 与 https 同行），CI 自动改写为 `[官方, gh-proxy.com/官方]` 镜像列表，conan 按序尝试，gh-proxy 在 CI worker 上实测可达（2026-08-06 实测 412KB/s）：

```yaml
# 修改前（单元素列表形态——CI 镜像注入被静默跳过）：
sources:
  url:
    - "https://github.com/Debian/apt/archive/refs/tags/2.7.14.tar.gz"

# 修改后（单值官方 URL——CI 注入 [官方, gh-proxy.com/官方]）：
sources:
  url: "https://github.com/Debian/apt/archive/refs/tags/2.7.14.tar.gz"
  sha256: "83dfebe76cfec8b33c1b83fddcd324328e4ecbf8ccf332501d682036546d0147"
```

**自检命令（提交前判定形态）**：

```bash
grep -E 'url:.*https://' conandata.yml
# 有输出 = 单值形态（镜像注入会触发）
# 无输出 = 列表形态，改回单条官方 URL
```

- CI 的 Mirror fallback 正则命中后会把单值改写成列表（官方 + gh-proxy.com/官方），conan 2 原生按序尝试，任一源成功即用（sha256 校验不变）；
- pre-download 段成功时改写 `file://` 后，列表内其他 URL 不受影响（提取/替换按完整 URL 串）；
- 本地验证：`conan create` 直连官方 URL（本地 github.com 可达）或模拟 CI 注入后的列表均能通过。

## 4. 降级方案

1. 换 worker 重试：撞到有 curl + github 可达的机器 pre-download 成功——治标不治本，随机红绿依旧；
2. 官方 URL 已失效、必须用镜像站时：仍保持**单值**形态，URL 直接写 gitee/gitcode 镜像地址，sha256 对镜像内容重算（E549 fallback 同款，chmlib/folly 先例）——切勿把镜像写成第二个列表项（那会同时关掉 CI 注入且 conan 按序尝试时镜像在官方之后救不了官方源失败）；
3. 框架级修复：pre-download 段改用 python urllib、或 `shutil.which('curl')` 探测降级——属 CI 基础设施改动，须走单独框架 PR（W2 原子性）。

## 5. 红线

- ❌ 看到三连 curl fail 就改 http:// 或删 conandata 的 url（pre-download 会剥除且违反 R39）；
- ❌ 为"保险"把单值官方 URL 改写成手写列表——CI 的镜像机制比手写列表可靠，列表形态反而关掉注入；
- ❌ 只修本地 conan 缓存 / 只在本地绿就提交——CI worker 网络与本地不同，须以 CI 实测为准；
- ✅ 单值官方 URL 第一（R39），sha256 保持官方源校验值不变；
- ✅ 提交前 `grep -E 'url:.*https://' conandata.yml` 确认单值形态。

## 6. 覆盖判断（查重展开）

| 既有条目 | 覆盖内容 | 本条增量 |
|---|---|---|
| E549（conandata 多 URL 列表→CI mirror fallback 静默跳过） | 多 URL 列表形态关掉 CI 镜像注入，解法为单值官方 URL | 本条是**单元素列表**特例：conan-init **自动生成**的默认形态就踩坑（无需手写多 URL），且叠加 worker 无 curl + host 不可达双因子 |
| DRAFT-ci-predl-curl-missing-conandata-mirror-list-fallback | worker 无 curl → pre-download 三连 fail 是良性噪音，WARN 降级 conan 接管 | 该条假设"conan 接管后官方 URL 可达"（KDE download.kde.org 可达场景）；本条证明**当官方 host 也不可达时，接管照样死**——救命的唯一路径是 CI 镜像注入，而它被列表形态关掉了 |
| DRAFT-ci-worker-curl-missing-predownload | 三连 curl fail 三要素判别法（良性噪音 vs 真红因） | 本条是 3b 分支（conan create 的 source() 也死）→ 需动配方：改回单值形态 |
| E017（GitHub 下载慢/超时→ghfast） | 单 URL 场景镜像**替换** | 本条聚焦**形态**而非域名：列表形态连 CI 注入都触发不了 |
| E299（conan source 失败分层诊断） | source() 失败分类框架 | 本条给出配方侧可执行修法（单值形态）+ CI pre-download 交互 |

## 7. 复现方法（自含）

- 观测：CI #85897 完整日志——pre-download 段三连 `[Errno 2] No such file or directory: 'curl'` → `[WARN] Failed to pre-download ..., will rely on conan's download` → conan source() 阶段 `Connection to github.com timed out. (connect timeout=30)`；
- 本机模拟：`grep -qE 'url:.*https://(github\.com)/' archives/a/apt-pkg/2.7.14/conandata.yml` → 无输出（列表形态，注入跳过）；改成单值后 → 有输出（注入触发）；
- 验证修法：conandata 改单值后 `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`——本地直连官方（可达）或 CI 经 gh-proxy 注入列表，任一成功即过。

## 8. 证据链

- 修前红：#85897（2026-10-12，OpenHarmonyPCDeveloper-CI-030，conan-build-test ❌）：pre-download curl×3 fail → conan source() github.com 30s 超时；诊断类别"网络问题/源码下载超时"；
- 对照历史：#80045 时 github.com 可达（source() 下载成功），失败在 SDK 探测（已由 ab90d78c 修复）；#85667 CMake 配置失败——#85897 是纯网络 + URL 形态双因子，与编译无关；
- 修法 commit：PR #14901 待推送（conandata.yml 列表形态 → 单值官方 URL）。
