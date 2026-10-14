# Draft: 源码住在发行版包管理器树内（无上游 tarball）的获取范式 — 逐文件 download() 固定 commit

## 使用说明

适用场景：上游**不发布任何源码归档**——源码直接提交在某个发行版/生态的包管理器
仓库树里（FreeBSD ports `MASTER_SITES=none`、pkgsrc、Homebrew head-only、
部分 Linux distro 的 in-tree 源码 patch 集）。此时没有可写进
`conan_data["sources"]` 的 tarball URL，也没有官方 SHA256 可抄。

本文给出一套可复现、可过 CI 的获取范式与决策顺序。

## 适用范围

- 正向：源码为包管理器树内少量**独立文件**（单 .c/.py + README + 伪造 Makefile），
  总量小、无子模块、无二进制 asset。
- 负向（不适用）：
  - 树内源码需配合该包管理器的构建框架才有意义（如 bsd.port.mk 的
    `USES=uidfix` 片段 Makefile——这类文件**不要**打包、不要执行）；
  - 树内文件随 main 分支漂移且无法定位稳定 commit；
  - 源码量大或含子模块（此时应联系上游发 tarball 或换 fork 托管，另立任务）。

## 输入 / 输出定义

输入：
- 包管理器仓库 URL（codeberg/github/gitlab 均可）+ 包目录路径；
- 一条 `commits?path=<dir>` 的 API 查询（或等价 git log）取该目录**最后一次
  变更 commit**；
- 每个需要的文件名。

输出（全部落进 conanfile.py，**不引入 conandata.yml**）：
- `_files_base = "<repo>/raw/commit/<full-sha>/<dir>"`（用完整 sha，短 sha 在
  codeberg raw 端点 404）；
- 每文件一个 `_sha256`（本机下载后 `Get-FileHash`/`sha256sum` 固化）；
- `source()` 内逐文件 `download(self, url, name, sha256=...)`。

## 示例

```python
from conan.tools.files import download

_ports_commit = "86b2c5122a18d1f73e6e4e4626889fab8fb0803a"
_files_base = ("https://codeberg.org/FreeBSD/freebsd-ports/raw/commit/"
               + _ports_commit + "/benchmarks/raidtest/files")

def source(self):
    download(self, f"{_files_base}/raidtest.c", "raidtest.c",
             sha256="70cb13...")   # 实际写完整 64 位
    download(self, f"{_files_base}/README", "README",
             sha256="643074...")
```

## 为什么不用别的路（决策顺序）

1. **不要**为本包自造 tarball 上传私仓：不可复现、引入私有依赖。
2. **不要**用 `get()`/`get(**conan_data["sources"])`：单文件 raw URL 没有
   `.tar.gz` 后缀，任何基于"下载后解压"的路径都会被格式推断坑（BadZipFile
   家族）；`download()` 只校验不解压，天然绕开。
3. **不要**写 conandata.yml：CI 对 conandata.yml 的 pre-download 路径有
   `BUILD_DIR: parameter not set` 基础设施缺陷，且镜像 fallback 会改写它；
   逐文件 download() 两条都不沾。
4. 取**目录最后变更 commit**而非 main 分支 HEAD：main 上无关 commit 会让
   SHA256 无故失效；目录级 commit 把漂移面压到"本包目录被改才失效"。
5. 包管理器自带的构建文件（ports 的 Makefile 是 bsd.port.mk 后端片段）必须
   弃用并在 notes 说明原因——它们离开该包管理器框架没有意义，build() 直接
   用 Conan 提供的编译器编单翻译单元即可。

## 验证命令

```sh
# 取目录最后变更 commit（完整 sha）
curl -s "https://<host>/api/v1/repos/<org>/<repo>/commits?sha=main&path=<dir>&limit=1" | jq -r .[0].sha
# 固化每个文件的 sha256
curl -sfL "<files_base>/<file>" | sha256sum
```

source_event: raidtest 1.3（FreeBSD ports benchmarks/raidtest，MASTER_SITES=none）
——2026-10-04 HarmonyOS PC 适配，r3 真机全门禁 pass。
