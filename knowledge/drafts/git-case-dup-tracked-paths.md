# DRAFT: git 大小写双路径分裂（HMDFS 协作仓）

## 现象

`git status` 永远显示同一目录下 2 个文件 M（路径大小写交替出现）；
`git pull --rebase` / `git stash` 全部落入死循环：

```
git stash            → 成功
git status           → 仍有两个 M（路径换成另一种大小写）
git pull --rebase    → error: cannot pull with rebase: You have unstaged changes
git stash pop        → M 又回来
```

## 根因

仓库历史上以不同大小写提交过同一目录，git index 中存在两套 tracked
路径（实证：build_in_harmonyos `archives/l/libXext` 大写 4 文件 +
`libxext` 小写 34 文件）。HMDFS 大小写不敏感，物理目录项只呈现一种
形态，两套 tracked 路径都 stat 命中它——任何写回操作都让另一套变脏。

无效手段（实测）：两步 mv 刷新大小写（仅对单路径幽灵有效）、
`git checkout HEAD --`、`rm + checkout` 重建、反复 stash。

## 逃生通道（推送被挡时）

```bash
git worktree add ~/tmp/wt origin/main -b fix-branch
cd ~/tmp/wt                       # 全新目录，物理大小写干净
git cherry-pick <目标提交>
git push origin HEAD:main
git worktree remove ~/tmp/wt --force
```

## 他人现场保护

分裂目录内未提交的实质修改：`cp` 备份到 `~/tmp`，操作完拷回。
（stash 对分裂目录无效，不要反复尝试。）

## 根治

需要一次专门 PR，在**大小写敏感 FS**（Linux/CI）上做：删除一套
tracked 路径（`git rm --cached` 小写那套），内容以权威版本为准。
HMDFS 本地无法根治。

## 检测

```bash
git ls-files | grep -i "^archives/l/libxext" | awk -F/ '{print $3}' | sort -u | wc -l
# 输出 >1 即分裂
```
