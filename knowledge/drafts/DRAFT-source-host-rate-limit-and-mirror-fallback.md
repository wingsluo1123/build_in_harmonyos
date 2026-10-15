# draft-source-host-rate-limit-and-mirror-fallback

## 症状

`conan create` 在 `source()` 阶段失败，三种面貌：

```
# (1) 限流
WARN: network: Error 429 downloading file https://codeberg.org/.../2.93.tar.gz
Waiting 5 seconds to retry...            （重试后仍 429）
ERROR: <pkg>: Error in source() method
       ConanException: Error 429 downloading file https://...

# (2) 拒连 / 不可达
WARN: network: Error downloading file https://files.pythonhosted.org/.../pox-0.3.7.tar.gz
ERROR: <pkg>: Error in source() method
       ConanException: Error downloading file https://...

# (3) 一个限流窗口罩住同主机全部端点（snac CI 第四轮）
WARN: [429] codeberg archive（两个 URL 都试过）
WARN: urllib 兜底（浏览器 UA 的独立客户端画像）也是 429 ×2
ERROR: source() method … CalledProcessError: [... 'git', …, 'fetch', …]
       returned non-zero exit status 128
       （rc=128 的原因看不到：CalledProcessError 不带 git 自身输出）
```

CI 的提示里已经写明处置方向：**"源码服务器返回 429 → 请稍后重试，或在 conandata.yml 中使用镜像源 URL"**。

## 诊断方法（重要陷阱）

本机 `curl` 对外全部失败：

```
curl: (60) SSL certificate OpenSSL verify result: unable to get local issuer certificate (20)
```

这是 **worker/本机缺 CA 证书**，不是网络不通——用 `curl` 判断"源是否可达"会得到全 000 的假阴性。
改用 python 的 urllib 探测（同一环境可正常建连）：

```python
import urllib.request, hashlib
u = "https://.../pkg.tar.gz"
with urllib.request.urlopen(u, timeout=30) as r:
    data = r.read()
print(r.status, len(data), hashlib.sha256(data).hexdigest())
```

**判断镜像可用性的唯一标准**：候选 URL 返回 200，且**下载字节的 sha256 与 conandata 记录一致**
（多数镜像原样回源，sha 相同；若不同则说明镜像重打包，不能直接替换）。

## 修复：conandata.yml 的 url 列表

仓库既有约定是**镜像/代理在前、官方源兜底**（见 `archives/a/aaphoto/0.45/conandata.yml` 的
一串 gh-proxy 变体）。`conan get()` 会按顺序尝试。

```yaml
sources:
  # 源可达性证据（实测日期 + 状态码 + 字节数 + sha256），便于复核
  url:
    - "https://<mirror-1>/<same-path>"
    - "https://<mirror-2>/<same-path>"
    - "https://<official>/<same-path>"
  sha256: "<不变>"
```

实测两例：

| 包 | 原源问题 | 换用 | 结果 |
|---|---|---|---|
| snac/2.93 | codeberg archive 路径 **429 限流**（CI 多轮同因） | 第一轮改 Forgejo API 端点——**被 CI 第二轮证伪**：archive 与 API-archive 同桶，双双 429。第二轮的裸 `git` 兜底——**被 CI 第三轮证伪**：worker PATH 没有 git。第三轮的"三级 source()"——**被 CI 第四轮证伪**：一个限流窗口同时罩住 archive、API、urllib 兜底与 **git HTTP 端点**（fetch rc=128）。终态：`source()` **四级化**——conan 下载器 → 纯 urllib（浏览器 UA + 声明 sha256）→ **atomgit 镜像分支浅克隆**（CI 主机自己的 forge，克隆流量常态可达；内层 tarball 与官方 archive 字节一致，同一 sha256 钉死）→ codeberg git 端点（fetch 60s 退避重试 ×3 + git 输出透出） | urllib 层与镜像层同一 sha256 校验；git 层树与官方 tarball **逐字节一致**（110 文件 0 差异），pinned peeled commit `795355ac` fetch 后校验 |
| pox/0.3.7 | `files.pythonhosted.org` **Errno 111 连接被拒**（本地复现一致） | 清华 `pypi.tuna.tsinghua.edu.cn/packages/...` 与阿里 `mirrors.aliyun.com/pypi/packages/...`（PyPI 文件镜像保持同路径） | 均 200、119442 字节，**sha256 与官方一致** |

## 兜底升级：四级 source()（tarball 全灭时）

**CI worker 的工具面事实**（snac 多轮实测得出，适用于所有 source() 兜底设计）：
worker PATH（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`）里
**没有 git、没有 curl、没有 tar**——只有 python3（其 urllib+TLS 可用，brotlicffi
的 conan 下载器与 pip 下载都正常）。所以：

- 任何兜底**不能假设 git/curl/tar 存在**；
- 公共 HNP 里有 git（`/data/service/hnp/bin/git`，与 profile 的 clang 同目录）但
  **不在 PATH**：要用 `shutil.which("git") or 绝对路径`，且必须设
  `GIT_EXEC_PATH=<git 所在目录>`（https remote-helper 同样不在 PATH；
  worker 模拟环境 `PATH=/system/bin` 下 init→fetch→checkout→rev-parse 全链实测可用）；
- atomgit 的匿名 raw/archive/contents 端点返回 HTML（SPA 兜底页）或 404，
  **取不到原始字节**——但**镜像 branch + 浅克隆**可以：把 tarball 提交到一个
  分支，匿名单分支浅克隆即可取回；这是 CI 主机自己的 forge，克隆流量常态可达，
  不在外部源站的限流窗口内，再用声明的 sha256 钉死字节；
- worker 与本机同机（buildbot 工作目录即本机缓存）：本机的网络探测结果对 worker
  直接成立；但限流是**时间窗口型，且可能罩住同主机全部端点**——snac CI 第四轮里
  codeberg 的 archive、Forgejo API、浏览器 UA 的 urllib 同时 429，连 git HTTP
  端点的 fetch 也失败（rc=128）。所以兜底要落到**别的服务/主机**上，
  不能只指望"换个端点"或"窗口内重试"。

四级结构（实测见 `archives/s/snac/2.93/conanfile.py`）：

```python
def source(self):
    try:
        get(self, **self.conan_data["sources"], strip_root=True)   # tier 1 conan 下载器
        return
    except Exception:
        ...

    # 共用助手：sha256 校验 + filter="data" 解包 + strip_root
    def _extract_tarball(data):
        if hashlib.sha256(data).hexdigest() != sha256:
            raise ConanException("tarball sha256 mismatch")
        ...extractall(self.source_folder, filter="data")...展平唯一顶层目录...

    # tier 2: 纯 urllib 拉同一 archive——独立客户端画像（浏览器 UA），
    # 声明的 sha256 钉死字节，不符即弃
    for url in urls: ... _extract_tarball(data); return

    # git 层共用：绝对路径解析 + GIT_EXEC_PATH（PATH 里没有 git），
    # 且必须自己捕获输出——CalledProcessError 只给 rc，不给原因
    def _git(*args):
        proc = subprocess.run([git, *args], env=env, stdout=PIPE, stderr=STDOUT)
        if proc.returncode != 0:
            raise ConanException("git %s failed (rc=%s): %s"
                                 % (args[0], proc.returncode,
                                    proc.stdout.decode(errors="replace")[-400:]))

    # tier 3: atomgit 镜像分支浅克隆（别的 forge，避开限流窗口）
    _git("clone", "--depth", "1", "--branch", _MIRROR_BRANCH, _MIRROR_URL, mirror)
    data = open(os.path.join(mirror, _MIRROR_FILE), "rb").read()
    shutil.rmtree(mirror)          # 解包前清掉，别干扰 strip_root 的单顶层目录判定
    _extract_tarball(data); return

    # tier 4: codeberg git 端点（最后兜底）：fetch 60s 退避重试 ×3 + 输出透出
    for attempt in range(3):
        try: _git("-C", tmp, "fetch", "--depth", "1", "origin", "refs/tags/<tag>"); break
        except ConanException: time.sleep(60)
    head = rev_parse("HEAD^{commit}")                               # 完整性锚点
    if head != _PINNED_COMMIT: raise ConanException(...)
    展平排除 .git
```

**没有 sha256 可校验时的完整性锚点**（tier 4）：

1. **钉死 peeled commit**：附注 tag 的 `refs/tags/<v>` 指向 tag 对象，`ls-remote` 里
   `<v>^{}`（peeled）才是 commit；fetch 后 `rev-parse HEAD^{commit}` 必须等于钉死值；
2. **一次性字节级比对**：克隆树 vs 官方 tarball 解包树逐文件 sha256（snac2 2.93：
   110 文件 0 差异，2026-10-14 实测），把结论与日期写进配方注释；
3. **展平排除 `.git`**；`shutil.move` 的目标目录必须已存在（`source_folder` 天然存在，
   自写探针要先 `os.makedirs`）。

## 判据小结

| 现象 | 结论 |
|---|---|
| `Error 429 downloading ...` | 源站限流：**先验证"另一端点"是否真的不同桶**（codeberg 的 archive 与 API-archive 同桶，换端点无效）；**一个窗口可能罩住同主机全部端点（连 git HTTP 一起）**——兜底要迁到别的服务/主机（如把 tarball 放到 CI 主机自己 forge 的镜像分支），别只换端点或只在窗口内重试 |
| `git ... fetch ... returned non-zero exit status 128` 且看不到原因 | `subprocess.run(..., check=True)` 的 `CalledProcessError` 只给 rc、不带 git 输出——自己捕获 stdout/stderr（合流 `PIPE`）并把截尾输出附进异常，否则 CI 日志无法定位 |
| `Error downloading ...`（无状态码） | 连接层失败（拒连/DNS/TLS）：直接换镜像 |
| `curl: (60) SSL certificate` | 是本机缺 CA，**不代表源不可达**；换 python 探测 |
| 镜像返回的 sha256 与记录不一致 | 镜像重打包过，**不能用**，继续找 |
| `FileNotFoundError: ... 'git'` 在 source() 兜底里 | worker PATH 无 git（也无 curl/tar）；用 `shutil.which or /data/service/hnp/bin/git` + `GIT_EXEC_PATH=其目录` |
| 只换 URL 不改 sha256 且构建通过 | 修复正确（源站内容未变） |

**附带结论**：CI worker 的 PATH 里**没有 git / curl / tar**（预下载步骤报
`No such file or directory: 'curl'`），只有 python3 的 urllib+TLS 可用——所以
预下载失败并不等于源不可达，最终以 conan 自己的下载器结果为准；source() 兜底设计
必须以"只有 python"为前提，且**层级要落在不同主机上**（snac/2.93 的四级 source()
即按此设计：conan 下载器 → urllib → 别的 forge 的镜像分支 → 上游 git 端点）。
