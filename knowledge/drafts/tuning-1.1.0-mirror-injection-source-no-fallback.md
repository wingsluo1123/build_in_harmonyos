# 镜像注入后 `source()` 丢掉官方源回退：失败点是下载通道，不是配方

> Draft: `DRAFT-MIRROR-INJECTION-SOURCE-NO-FALLBACK`
> Stem: `tuning-1.1.0-mirror-injection-source-no-fallback` — 与同 stem 的 `.kv` 配套

## 基本信息

- **ID**: DRAFT-MIRROR-INJECTION-SOURCE-NO-FALLBACK
- **严重度**: 2
- **类别**: network|source-url|ohos-platform
- **触发工具**: conan
- **阶段**: source|download

## 现象

tuning 1.1.0（header-only、零依赖、零补丁）在 `conan-verify` 的 G2 阶段失败：

```
ERROR: tuning/1.1.0@ohpcd/stable: Error in source() method, line 62
    get(self, **self.conan_data["sources"], strip_root=True)
    ConanException: Error downloading file https://ghfast.top/https://github.com/surge-synthesizer/
    tuning-library/archive/refs/tags/release_1.1.0.tar.gz: '...SSLError(SSLCertVerificationError(1,
    "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is
    not valid for 'ghfast.top'. (_ssl.c:1010)"))'
```

同一时刻的网络对照（真实输出）：

| 目标 | 结果 |
|---|---|
| `ghfast.top/https://github.com/...` | `http=000`（SSL hostname mismatch → ReadTimeout） |
| `gh-proxy.com/https://github.com/...` | `http=200`（1.86s） |
| `https://github.com/...`（官方直连） | `http=200`，size=140050 |

## 根因

ohc 的 `conan-verify`（G2，“E017 预防”）与 CI 的 `build_and_test.sh` 都会把
`conandata.yml` 里的 `https://github.com/...` 做**字符串替换**改成镜像地址
（本地用 `ghfast.top`，CI 用 `gh-proxy.com`）。替换后 `sources.url` 变成**单值**：

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)   # ← 只有镜像一个候选
```

镜像域不可达时 `get()` 没有第二候选，直接抛异常 → 干净构建判失败。
**失败与源码/配方无关**，是下载通道的镜像单点。

## 修复（配方侧，不碰基础设施）

`source()` 里显式构造 URL 列表：把（可能已被改写成镜像的）url 取出后追加官方源，
与 CI `get_mirror_list` 的 `[mirror, url]` 口径一致；`sha256` 强校验保证完整性：

```python
OFFICIAL_SOURCE_URL = "https://github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz"

def source(self):
    src = dict(self.conan_data["sources"])
    urls = src.pop("url")
    if isinstance(urls, str):
        urls = [urls]
    if OFFICIAL_SOURCE_URL not in urls:
        urls.append(OFFICIAL_SOURCE_URL)
    get(self, url=urls, sha256=src["sha256"], strip_root=True)
```

复验：同一配方在 ghfast.top 仍不可达时 G2 PASS，G0-G4/L2/L4/L5 全通过。

## 诊断口诀

看到 `Error in source() method` 且报文里出现 `ghfast.top` / `gh-proxy.com` 域名
→ 先判**通道**（curl 该镜像域），不要改配方、不要用 `--no-preflight` 绕。

## 证据

- `archives/t/tuning/1.1.0/reports/conan-verify-run1-ghfast-down.log`（首轮失败原文）
- `archives/t/tuning/1.1.0/reports/conan-verify-run2-pass.log`（加入官方源回退后通过）
