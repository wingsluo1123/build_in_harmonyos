# DRAFT-ohos-offline-source-switch-criteria

> 维护者复审候选草稿（Path B 知识扩展材料）；**不自动作为 Path B 评级或分值依据**。

## 现象

在受限网络（本仓 CI/沙箱）里适配三方库时，上游发布位常常整体不可达，例如本轮实测：

| 上游发布位 | 实测失败形态 |
|---|---|
| `github.com/.../releases/download/...`（libcaca、samba 归档） | `urlopen error [Errno 110] Operation timed out` |
| `sourceforge.net/...`（libbs2b、nemesi） | `Failed to connect … port 443`（全镜像同） |
| `download.live555.com/...` | `301` 且 `Location` **畸形**（`https://download.live555.comlive.<date>.tar.gz`，域名与文件名之间缺 `/`） |
| `www.live555.com/...` | TLS `wrong version number`（协议不兼容） |

## 关键教训：官方替代源有两种形态，**不能只看“可达 + 哈希”**

以 `libcaca/0.99.beta20` 为例，可换的官方渠道逐一实测：

| 候选（均为官方渠道） | 结果 |
|---|---|
| Debian `libcaca_0.99.beta20.orig.tar.gz` | 可达，但展开为**源码快照**：**无 `configure`** ✗ |
| Void sources `libcaca-0.99.beta20/v0.99.beta20.tar.gz` | 与 Debian **同一份**（sha256 `3edb8763…84f2` 完全相同），同样无 `configure` ✗ |
| MacPorts distfiles `libcaca/libcaca-0.99.beta20.tar.gz` | 文件名同上游 release asset，但展开是 `cacalabs-libcaca-<sha>/`（**GitHub 归档**）→ 仍无 `configure` ✗ |
| **Fedora lookaside `libcaca-0.99.beta20.tar.bz2`** | **dist tarball**（893,319 B，**含 `configure`**），Fedora 记录的 sha512 逐字核验一致 ✓ → 采用 |

若只验哈希，前三份都会“通过”，然后在构建期以 `configure script is missing` 失败（本机 conan 侧 `autoreconf`
又因 perl 模块 `Cwd.so` 重定位失败而不可用，见下），排查成本很高。

## 其它边界（本轮实测）

- **Debian 的 `+dfsg` 版本**：属**下游重打包**（删改内容），按仓内 R39/PF7 不宜作替代源。
- **SourceForge 官方镜像主机**：`master.dl.sourceforge.net`、`netix.dl.sourceforge.net` 等只返回
  `301 → https://downloads.sourceforge.net/...`（即回到本项目域名）；当 sourceforge 整体不可达时，镜像链无效。
- **对已消亡的上游无解**：`nemesi`/`libnetembryo` 在 SF 镜像、MacPorts（404）、Software Heritage（`[]` 无 origin）、
  FreeBSD distcache（无响应）全部不存在 → 属上游事实消亡，不是网络受限问题。

## 推荐处置

1. 优先**上游官方发布位**：本轮 `download.samba.org` / `download.gnome.org` / `x.org` / `videolan` 均可达。
2. 不可达时用**官方发行版源码缓存**：优先 Fedora lookaside（`src.fedoraproject.org/repo/pkgs/<name>/`，多为 dist tarball），
   其次 Debian pool、MacPorts distfiles、Void sources、openSUSE / Alpine / Arch / Gentoo（本轮实测均可达）。
3. **落盘前校验内容**：解开展开目录名与生成物 —— autotools 配方必须有 `configure`（否则等价于快照，需 autoreconf）。
4. **双重哈希核验**：用缓存记录的强哈希（Fedora sha512 / md5）逐字核对，并把 sha256 写进 `conandata.yml`；
   换源理由（含被排除的候选）写进 `conandata.yml` 注释与 `notes.md`，便于复审。
5. 快照类源只有在**能提供 autoreconf** 时才考虑（本环境 conan 侧 autoreconf 不可用：`automake/1.18` 携带的 perl
   模块 `Cwd.so` 加载即报重定位失败），因此实践中一律优先 dist tarball。

## 证据

- `archives/l/libcaca/0.99.beta20/notes.md`（换源记录，含 4 份候选的逐一排除与 sha512 核验）
- `archives/l/libcddb/1.3.2/conandata.yml` + `notes.md`（Debian pristine orig 采用）
- `archives/l/libbs2b/3.1.0/notes.md`（sourceforge → Fedora；并排除 dfsg）
- `archives/l/live555/2026.08.14/conandata.yml`（301 畸形/TLS 失败 → Fedora lookaside）
- `archives/s/samba/4.21.0.1/notes.md`（GitHub 归档 → 官方发布位；含“基线仅换源”的对照实验）
