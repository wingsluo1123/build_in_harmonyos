# Draft: 设备存储配额真满时 shadow CI 隔离 job 的替代构建流程 — 写探针判空间、`git archive HEAD` 瘦快照、手工组装 job 骨架

## 使用说明

适用场景：真机 shadow CI 创建隔离 job 时 `ohos-prepare-isolated-conan-job.sh
--repo-source` 复制 repo 中途报 `No space left on device`，且现有两条
ENOSPC 草稿不适用——本条针对**真空间/配额耗尽**（coordgenlibs/dmc_unrar
讲的是 inode 池耗尽且磁盘未满，解法是 sparse-checkout，这里救不了）。

给出三步替代流程：①用写探针（而非 df）判定真实可用空间；②用本机
`git archive HEAD` 生成瘦快照替代全量 repo 拷贝；③手工组装 job 骨架
（目录契约 + env.sh + runner 模板），跳过 ohos-prepare 脚本。

## 适用范围

- 正向：设备用户分区（HMDFS）配额/空间真满，无法容纳 `--repo-source` 的
  全量 repo（含 `.git` 历史，通常数 GB）；需要在设备上继续跑 shadow CI。
- 负向：
  - inode 耗尽但磁盘有空间（走 coordgenlibs/dmc_unrar 的 sparse-checkout）；
  - repo-source 缺 ci/ 或索引污染（走 DRAFT-ntldd-0.2 / DRAFT-13618 的
    完整性预检与换源）——本流程顺带免疫这两类问题（快照来自本机 HEAD）；
  - 仅想省时间而空间充足（此时标准脚本流程更简单，别手工组装）。

## 输入 / 输出定义

输入：本机同仓库 worktree（HEAD 与任务分支一致）、设备 SSH 可达、一个
近期健康 job（提供 runner/env 模板与 repo 内容基线）。

输出：设备上 `$HOME/ohos-users/codex/<job>/` 完整 job（repo/ conan-home/
work/ artifacts/ logs/ env.sh run-conan-heavy.sh），可被
`run-conan-heavy.sh` 正常驱动，与脚本创建的 job 等价。

### 判定空间：不要信 df，用写探针

HMDFS 的 df 输出会显示 tmpfs 16G / 或挂到 `non_account` 卷显示数百 GB 可
用——**全部不可信**（fuse 层失真）。唯一可靠判据是实际写入：

```sh
dd if=/dev/zero of=$HOME/.wtest bs=1M count=500 2>&1 | tail -1
rm -f $HOME/.wtest
# 0 B copied = 满；完整 500M = 至少有 500MB
```

### 瘦快照：为什么是 git archive HEAD

- `git archive --format=tar.gz HEAD` 从**树对象**生成，不含 `.git`（省掉
  数 GB 历史），本仓 115020 文件实测 165MB；
- 磁盘无关：Windows/HMDFS 大小写不敏感文件系统上，上游同时含
  `libXext/` 与 `libxext/` 两套路径时工作区检出必然互相覆盖、`git status`
  永久脏；archive 按 HEAD 树输出，顺带解决这一检出污染（同机制另见
  iroffer 草稿的大小写折叠误判，本文是它的检出侧解法）；
- 也顺带免疫 repo-source 系草稿的"快照缺 ci/"与"暂存文件继承"两类缺陷。

与既有条目的分工与警示：
- E326/E256（正式条目）已确立"Shadow CI 验证对象 = git archive HEAD 快照、
  dirty worktree 不会自动进入验证"这一**语义**；本文不是重复该警示，而是
  把同一机制**反向用作**设备空间受限时替代全量 repo 拷贝的传输方案，并补齐
  手工组装 job 骨架的完整契约。沿用 E326 的推论：快照只含已提交内容——
  **走本流程前必须先 commit 本库改动**（否则验证的不是你改过的配方）；
- 存储受限的姊妹判定：coordgenlibs/dmc_unrar 讲 inode 池耗尽（df 有空间、
  仍 ENOSPC，解法 sparse-checkout）；本文讲真配额/空间满（df 不可信、
  dd 写探针判真），两者先按 `df -i` 与写探针区分再选路线。

## 手工组装契约（缺一即 runner 起不来）

```sh
JOB=$HOME/ohos-users/codex/<job>
mkdir -p $JOB/repo/build_in_harmonyos $JOB/conan-home $JOB/work $JOB/artifacts $JOB/logs
cd $JOB/repo/build_in_harmonyos && gzip -dc <snapshot>.tar.gz | tar -xf -
```

env.sh 必备变量（从近期健康 job 抄，改三处：JOB 名、CI_REPO_ROOT、
CI_PACKAGES）：

```sh
export OHOS_ISOLATED_USER='codex'
export OHOS_ISOLATED_JOB='<job>'
export OHOS_JOB_BASE='<JOB 绝对路径>'
export CONAN_HOME='<JOB>/conan-home'
export CI_REPO_ROOT='<JOB>/repo/build_in_harmonyos'
export CI_PACKAGES='archives/<首字母>/<库>/<版本>'
export CONAN_PROFILE=${CONAN_PROFILE:-ohos-aarch64}
export PATH=$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:$PATH
export PYTHONPATH=$HOME/ohpc-ci-shadow/python-user/lib/python3.12/site-packages:${PYTHONPATH:-}
```

run-conan-heavy.sh（逐字复刻健康 job 的，语义 = `ohos-test-runner.sh
--lock 排队 + zsh ci/conan/build_and_test.sh $CI_PACKAGES`）。

**传输注意**：设备 `/tmp` 只读，远端写文件一律 `scp`（含 job 骨架文件，
heredoc 必失败）；传输后按自检模板 2.3 验证包目录文件清单。

## 示例（真实事件，raidtest 1.3）

`--repo-source` 两次中断（cp 报 ENOSPC，且连清单文件都写不进）→ 清理
`$HOME` 顶层散落 tar/log（~170MB）+ 残缺 job → 500MB 写探针通过 →
本机 `git archive HEAD | 165MB` → scp → 手工组装 → runner r3 exit 0
全门禁 pass。注意：清理只动了自己创建的残缺 job 与顶层散落文件；
**他人 job 与历史批次未经授权一律不删**。

## 验证命令

```sh
# job 等价性自检（起 runner 前跑完这组）
ls $JOB                          # 6 项齐全
ls $CI_REPO_ROOT/ci/conan/build_and_test.sh $CI_REPO_ROOT/ci/conan/profiles/ohos-aarch64
find $CI_REPO_ROOT/archives/<首字母>/<库>/<版本> -type f | sort   # 包文件齐全
sh -n $JOB/run-conan-heavy.sh && echo RUNNER_SYNTAX_OK
grep CI_PACKAGES $JOB/env.sh     # 确认指向本包（防 maxflow 草稿的默认包陷阱）
```

source_event: raidtest 1.3 shadow CI（2026-10-04）：--repo-source 两次
ENOSPC 中断后走本流程，r3 真机 exit 0 全门禁 pass。
