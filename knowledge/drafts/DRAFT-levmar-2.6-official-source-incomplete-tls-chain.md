# DRAFT: 官方源 TLS 证书链不完整（缺中间 CA）的判别与处置

- **ID**: `DRAFT-levmar-2.6-official-source-incomplete-tls-chain`
- **触发工具/阶段**: conan | curl | openssl — download（`source()` 阶段）
- **严重度**: 2（🟡 中等）
- **类别**: network, conan, download, tls, ohos
- **来源**: levmar 2.6 适配（OHOS PC aarch64，官方源 `www.ics.forth.gr`，2026-10-18）

## 错误特征

```
# conan（source() 阶段，首错）
conanfile.py (levmar/2.6): WARN: network: Error downloading file
  https://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz:
  'HTTPSConnectionPool(host='www.ics.forth.gr', port=443): Max retries exceeded ...
   (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
   certificate verify failed: unable to get local issuer certificate (_ssl.c:1082)')))'
ERROR: levmar/2.6: Error in source() method
       ConanException: Error downloading file https://www.ics.forth.gr/...

# curl（未加 -k）
curl: (60) SSL certificate problem: unable to get local issuer certificate

# services 侧
verify return code 21 (unable to verify the first certificate)
```

## 场景

`levmar 2.6` 的官方 tarball 只挂在作者单位站点（非 GitHub），`conandata.yml`
必须写该官方 URL。`conan create` 在 `source()` 阶段直接失败，无法进入编译。

## 根因（一手证据）

服务端 **TLS 握手只发送 2 张证书**：叶证书 `CN=ics.forth.gr`（签发者
`GEANT TLS RSA 1`）+ `HARICA TLS RSA Root CA 2021`，**缺签发叶证书的中间 CA**。

```bash
$ openssl s_client -connect www.ics.forth.gr:443 -servername www.ics.forth.gr -showcerts </dev/null 2>/dev/null | grep -c "BEGIN CERTIFICATE"
2
$ openssl s_client -connect www.ics.forth.gr:443 -servername www.ics.forth.gr </dev/null 2>/dev/null | grep "Verify return code"
    Verify return code: 21 (unable to verify the first certificate)
```

**判别关键：这不是本机缺 CA。** 同一个 CA bundle（Mozilla/certifi，121 张证书）
对其他主机全部正常：

```bash
$ curl -sS -o /dev/null -w "%{http_code}\n" https://curl.se/ca/cacert.pem     # 200
$ curl -sS -o /dev/null -w "%{http_code}\n" https://api.gitcode.com/api/v5/version   # 404（TLS 已通过）
```

这条与 E185 / E034（客户端缺 ca-certificates ⇒ 装 CA 包或临时 `-k`）**根因不同、
解法不同**：此处任何客户端信任库改动都无济于事（除非把该中间 CA 当根装进信任库），
而 `-k` / `--no-check-certificate` / `verify=False` 在本仓一律禁止（放弃来源验证）。

## 处置

**判别先行**（上面三步跑完再决定动作；本条的判别法就是它的主要价值）：

```bash
# a) 服务端到底发几张证书、openssl 怎么判
openssl s_client -connect <host>:443 -servername <host> -showcerts </dev/null 2>/dev/null \
  | grep -c "BEGIN CERTIFICATE"        # 2 + Verify return code 21 == 缺中间 CA
# b) 排除本机信任库：同一个 bundle 必须能校验别的主机
curl -sS -o /dev/null -w "%{http_code}\n" https://curl.se/ca/cacert.pem    # 200 == bundle 没问题
# c) 是否还有同一官方站点的其他入口可用（**先查作者官方下载页上的链接**）
curl -sS -o /dev/null -w "code=%{http_code} size=%{size_download} redirect=%{redirect_url}\n" <候选入口>
```

**处置一（首选，已实测）：改用作者官方下载页列出的官方入口直链，并保持 sha256 不变。**
服务端证书链不完整时，同一官方站点的另一个主机名/入口常常仍提供**逐字节相同**的归档
（先例：levmar 2.6，`https://www.ics.forth.gr/...`（缺中间 CA，恒失败）→ 作者官方页
`http://users.ics.forth.gr/~lourakis/levmar/` 上「Latest」指向的
`http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz`，`200 / 81143 字节`，
sha256 与 conandata 记录值**逐字一致**）。要点：

- 先算候选入口下到的文件 sha256，**必须与 conandata 现记录值逐字相同**才可改；
  不同 ⇒ 不是同一制品，⛔ 不得改用它、不得顺手改 sha256 去迁就。
- `sha256` 字段**不动**：完整性由内容哈希固定，**不依赖传输层**，这也是明文 http
  在此场景可接受的前提。
- 该入口必须是**作者/上游官方站点自身**（官方下载页上的链接或其同一站点主机名），
  ⛔ 不是第三方代理/镜像/池/重打包。
- 若候选入口是明文 `http`，会触发 `scripts/ohc/preflight.py` 的 **PF7 源URL闸**
  （实测读数：`PF7 源URL闸(R39): … 明文 http 源（R39 要求 https）`）。
  PF7 自身给出的处置是「确属**官方托管例外**须 PR 说明并 `--no-preflight` 跳过」
  ⇒ 走**显式例外**（PR 正文写清：症状、官方性佐证、sha256 逐字一致的两次读数、
  两行复现命令），⛔ 不是静默跳过、⛔ 更不是关校验。

**处置二（辅助/仅本机）：按内容 sha256 预置共享下载缓存**
（`core.sources:download_cache`，机制细节见 `经验库 §12.55`）：缓存键 =
**文件内容的 sha256**（不是 URL 哈希）`s/<sha256>`；先 `rm -f s/<sha256>.dirty`；
sidecar `<sha256>.json` 必须是合法 JSON 且 `references` 覆盖请求 URL 与配方引用
（`<pkg>/<ver>` 与 `<pkg>/<ver>@<user>/<channel>`）；命中证据只看构建日志
`retrieved from local download cache`。⚠ **该缓存不随 PR 进 CI**，单独用它只能让
本机变绿，CI 仍会红（本条的实战教训：CI 预下载兜底在该链路还缺 `curl` 本体
`[Errno 2] No such file or directory: 'curl'`，取源完全依赖 conan 自身下载路径）。

**验证（唯一可接受的证据 = 日志原文）**：把 dlcache 条目先移走以强制真下载，
然后看构建日志出现

```
Sources correctly downloaded from <改后 URL>
```

（conan 命中 sha256 不符会直接抛 `ConanException`，故该行同时证明内容校验通过。）

## 反例 / 禁止项

- ⛔ 在配方或 CI 里加 `-k` / `--no-check-certificate` / `verify=False`：等于放弃
  tarball 的来源验证。
- ⛔ 把 `conandata.yml` 改成**非官方**的 `http://` 地址（第三方镜像/代理/池/重打包）：
  PF7 明文 http 与镜像黑名单直接拦。官方托管例外是**例外**（须官方性佐证 + PR 说明 +
  显式跳过），不是"http 随便写"。
- ⛔ 改 sha256 去迁就另一个入口/重打包件：那是换制品，不是修取源。
- ⛔ 因为"curl 连不上"就断定"本机缺 CA"并去装 CA 包：本条的判别法（证书计数 +
  同 CA 正常主机对照）必须先跑。

## 与既有条目的关系

- E185 / E034：症状字面相同（`unable to get local issuer certificate`），但根因是
  **客户端信任库缺失**，解法（装 CA 包 / 临时 `-k`）对服务端缺中间 CA 无效 ⇒ 本条
  是"另一条解法 + 判别法"，非重复。
- E017 / `经验库 §12.55`：讲受限网络下的镜像与下载缓存预置机制；本条补的是
  **为什么官方 URL 会失败**（服务端证书链不完整）、**如何列出并验证同一官方站点的
  其他官方入口**，以及**镜像映射表覆盖不到时的残余风险与官方托管例外口径**。
- E299：源码获取失败的分层诊断（含 `SSL certificate problem` 分类），未给出
  服务端证书链不完整的判别步骤与同官方入口回退处置。

## 适用范围与解除条件

- 适用：任何 `conandata.yml` 指向**非 GitHub 官方/权威 https 主机**、且该主机服务端
  证书链不完整的包。
- 解除：上游修复证书链（或平台把缺失的中间 CA 加入 worker 信任库 / 把该域名纳入镜像
  映射表）后，即可把 url 换回 https 官方入口，并去掉官方托管例外说明与 dlcache 预置。
