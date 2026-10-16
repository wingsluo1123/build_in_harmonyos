# Git 2.56.0 鸿蒙 PC 使用指南

> 适用：HarmonyOS PC（aarch64）上自编译的 git 2.56.0（`/storage/Users/currentUser/usr/local/bin/git`）
> 与 Linux 常规使用的差异均在本文说明，实测验证于 2026-10-14

---

## 一、启用方式

**自包含静态构建**：curl/openssl/zlib 已静态链入二进制（`readelf -d` 显示仅依赖系统 libc.so），无需任何动态库路径：

```bash
export PATH=/storage/Users/currentUser/usr/local/bin:$PATH   # 唯一必需
git --version                                                 # git version 2.56.0
```

`~/.ohos_git/env.sh` 仍可用（向后兼容，其中的 LD_LIBRARY_PATH 已是多余但无害）。

**说明**：早期动态构建版本需要 `LD_LIBRARY_PATH` 指向 conan 缓存的 libcurl/libssl，现版本已静态化，整个 `usr/local` 目录拷贝到其他鸿蒙 PC 即可用。

---

## 二、配置文件保存路径差异（重点）

git 的配置分三层，每层的实际路径都与 Linux 不同：

| 层级 | Linux 惯例 | 鸿蒙 PC 实际（2.56.0） |
|---|---|---|
| system | `/etc/gitconfig` | `/storage/Users/currentUser/usr/local/etc/gitconfig`（编译前缀决定） |
| global | `~/.gitconfig` | `/storage/Users/currentUser/.gitconfig`（HOME=/storage/Users/currentUser） |
| local | 仓库内 `.git/config` | 同 Linux（相对仓库，无差异） |

### ⚠️ 新旧版本 global 路径不一致

系统预装 git 2.45.2 的 global 配置被定制到 **`.ohos_git/.gitconfig`**，而 2.56.0 用标准 **`~/.gitconfig`**——两个文件互不感知：

```bash
# 2.45.2 读写：/storage/Users/currentUser/.ohos_git/.gitconfig（含历史身份与 safe.directory 条目）
# 2.56.0 读写：/storage/Users/currentUser/.gitconfig
```

**切换到 2.56.0 后首次使用需重新配置身份**（一次性，已在适配时为你同步完成）：

```bash
git config --global user.name  "你的名字"
git config --global user.email "you@example.com"
```

### system 层已预置的配置（勿重复配置）

`usr/local/etc/gitconfig` 已包含：

```ini
[safe]
    directory = *                     # 见下文"属主检查"说明
[http]
    sslCAInfo = .../usr/local/ssl/cert.pem   # Mozilla CA 包（121 个根证书）
```

HTTPS 克隆开箱即用，无需手动配 CA。

---

## 三、路径与环境速查

| 项 | Linux | 鸿蒙 PC | 说明 |
|---|---|---|---|
| 用户主目录 | `/home/<user>` | `/storage/Users/currentUser` | |
| 临时目录 | `/tmp`（可写） | **`/tmp` 只读！** | 脚本临时文件用 `$TMPDIR` 或 `$HOME/tmp` |
| bash | `/bin/bash` | **不存在**；实际在 `/data/service/hnp/bin/bash`，系统仅有 `/bin/sh` | 影响 hooks 的 shebang（见下） |
| CA 证书 | `/etc/ssl/certs/` | `/storage/Users/currentUser/usr/local/ssl/cert.pem` | system gitconfig 已指向 |
| 运行时依赖库 | `/usr/lib` 等 | `~/.conan2/p/*/p/lib`（env.sh 已注入） | curl/openssl/expat 为 conan 动态库 |
| perl | `/usr/bin/perl` | `/data/service/hnp/bin/perl` | 影响 git-svn/send-email 等 perl 脚本 |
| 磁盘文件系统 | ext4/btrfs 等 | HMDFS（分布式） | 带来权限/链接语义差异，见下 |

---

## 四、行为差异（HMDFS/系统带来的）

### 1. 属主检查（dubious ownership）——已根治，但仅限 2.56.0

鸿蒙用户分区的文件属主被统一映射（uid 20001006），与进程 uid 永不一致。git ≥2.35 的属主安全检查在此环境下**必然触发**：

- **2.56.0**：编译期已启用 `TRUST_ALL_REPOSITORIES`，任何仓库直接可用
- **2.45.2（系统预装）**：会报 `fatal: detected dubious ownership`，需逐仓库 `git config --global --add safe.directory <路径>`（这就是旧 `.ohos_git/.gitconfig` 里堆了大量条目的原因）

如果终端里看到 dubious ownership 报错，说明 PATH 命中了旧版——重新 `source ~/.ohos_git/env.sh`。

### 2. hooks 脚本的 shebang（最常见踩坑）

`#!/bin/bash` 会报 `cannot exec '.git/hooks/pre-commit': No such file or directory`（解释器不存在）。写 hooks 请用：

```bash
#!/bin/sh                          # 推荐，系统自带
# 或
#!/data/service/hnp/bin/bash       # 需要 bash 特性时
```

### 3. PATH 中新旧版本混用的隐蔽问题

2.56.0 的部分命令（如 `fsck`）会派生 `git-refs` 等子命令，按 PATH 查找。若 PATH 里旧版 2.45.2 在前，会得到莫名其妙的错误（`git: 'refs' is not a git command` 或 dubious ownership）。**始终确保 2.56.0 的 bin 目录在 PATH 最前**。

### 4. 硬链接与权限语义

- HMDFS **不支持硬链接**（`ln` 无 `-s` 时报 Operation not permitted）——git 2.56.0 构建已用 `NO_INSTALL_HARDLINKS` 规避，日常操作无感知
- 新建文件权限基线为 `660`（属主/组读写），`chmod +x` 对新文件生效，但特殊权限位（setgid 等）会被文件系统重写
- 依赖权限断言的脚本（如期望 `755`）可能行为不同

### 5. 中文文件名显示

与 Linux 默认行为一致：`git ls-files`/`status` 中非 ASCII 文件名默认转义显示（`\344\270\255...`）。想直显中文：

```bash
git config --global core.quotepath false
```

### 6. 性能预期

HMDFS 单文件操作延迟高于 Linux 本地文件系统，大仓库（数万文件）的 `status`/`gc`/`checkout` 明显慢于同配置 Linux 机器，属正常现象。实测参考：小仓库全工作流（init→commit→merge→clone）秒级完成；kernel.org `ls-remote` 约 6 秒。

### 7. 并发/内存约束（脚本作者注意）

高并发进程+大量文件 IO 会触发 HMDFS 页缓存在 cgroup 内累积，**实测并行度 >6 的批量任务可能耗尽系统内存**且恢复缓慢。跑批量脚本（含 `prove`、批量 `git clone`）建议并发 ≤4，并在批次间 sleep。

---

## 五、网络环境实测（2026-10）

| 目标 | 结果 | 说明 |
|---|---|---|
| kernel.org（https） | ✅ 可用（~6s） | |
| USTC 镜像（mirrors.ustc.edu.cn） | ✅ 快 | 源码下载首选 |
| GitHub | ❌ 连接超时 | 网络环境问题，非 git 问题 |
| Gitee 公开仓库 clone | ⚠️ 401 | Gitee 服务端对数据中心 IP 的风控，非 git 问题；浏览器登录态下不受影响 |

本地协议（路径、`file://`）与 ssh 协议（`/usr/bin/ssh` 可用）不受影响。

---

## 六、快速上手示例

```bash
# 1. 启用
source ~/.ohos_git/env.sh

# 2. 首次身份配置（若 ~/.gitconfig 尚无身份）
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"

# 3. 日常使用与 Linux 完全一致
git clone /path/to/repo           # 本地克隆
git init && git add . && git commit -m "first"
git ls-remote https://git.kernel.org/pub/scm/devel/sparse/sparse.git

# 4. 中文文件名直显（可选）
git config --global core.quotepath false
```

## 七、常见问题速查

| 症状 | 原因 | 解法 |
|---|---|---|
| `detected dubious ownership` | PATH 命中了系统 2.45.2 | `source ~/.ohos_git/env.sh` 后重试 |
| `cannot exec hook: No such file or directory` | hook 用了 `#!/bin/bash` | 改 `#!/bin/sh` 或 `#!/data/service/hnp/bin/bash` |
| `Error loading shared library libcurl.so` | 未加载 LD_LIBRARY_PATH | `source ~/.ohos_git/env.sh` |
| `SSL certificate problem` | CA 路径未配置 | 已预置于 system 配置；自签名场景用 `git -c http.sslCAInfo=<bundle>` |
| `git: 'refs' is not a git command` | 新旧版本混在 PATH | 确保 usr/local/bin 在最前 |
| `Read-only file system`（写 /tmp） | /tmp 只读 | 改用 `$TMPDIR` |
| `ln: Operation not permitted` | HMDFS 无硬链接 | 用 `ln -s`（软链）或 `cp` |
| `make: jobserver mkfifo` 失败 | HMDFS 无 fifo | `make -jN --jobserver-style=pipe` |

---

## 附：本版本适配要点（面向维护者）

- 4 个平台补丁：configure umask（HMDFS setgid）、pthread_setcancelstate 守卫（musl 裁剪）、TRUST_ALL_REPOSITORIES 宏、可选 Rust 组件移除
- **自包含静态链接**：curl（配方强制 shared=False，缺失时 CI 从源码构建）/openssl/zlib 静态链入；expat 已裁剪（NO_EXPAT，仅影响 WebDAV push 遗留协议，HTTPS fetch/push 不受影响）
- 依赖：zlib/openssl/curl 来自 conan 制品仓（ohpcd remote）
- 详细过程见同目录 `notes.md` 与 `reports/test-report.md`（34/34 手工验证 + 上游测试套件全系列）
