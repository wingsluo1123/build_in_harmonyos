# semtag

semtag 是一个 Git 语义化版本（SemVer）打标签工具，单文件 Bash 脚本。它只依赖仓库
自身的 Git tag：读取已有 tag，按 `-s major|minor|patch|auto` 推算下一个版本号，并可
直接创建带提交日志的附注 tag（`final` / `candidate` / `beta` / `alpha`）。

- 上游：https://github.com/nico2sh/semtag （tag `v0.2.0`）
- 许可证：Apache-2.0

## 交付内容

- `bin/semtag`：上游单文件脚本，应用了 1 个鸿蒙适配补丁（见下）。
- `share/doc/semtag/README.md`：上游文档。
- `licenses/LICENSE`：上游 Apache-2.0 许可证正文。

上游没有编译单元，也没有构建系统，因此本包没有编译步骤。

## 使用

```sh
# 在任意 Git 仓库中
semtag getlast                 # 最新 tag
semtag getfinal                # 最新正式版（忽略预发布）
semtag final -s minor -o       # 只显示下一个 minor 版本，不打 tag
semtag final -s patch          # 创建下一个 patch 版本的附注 tag
semtag alpha                   # 创建 -alpha.N 预发布 tag
```

## 运行时依赖

`bash`（>= 4.3：脚本使用关联数组、nameref、`mapfile`、进程替换）与 `git`，以及
`id`、`hostname`、`date`、`awk`、`wc`、`xargs` —— 都是操作系统自带工具，不是 Conan 包，
因此配方没有 `requires`/`tool_requires`。

## HarmonyOS 适配

单个补丁 `patches/0001-semtag.patch`，一处改动：

- **shebang → `/data/service/hnp/bin/bash`**（知识条目 E037）。鸿蒙没有 `/usr/bin/env`，
  bash 位于 hnp 前缀下。不改则安装后的 `semtag` 无法直接执行，而软件级
  `commands.json` 声明的正是直接执行 `bin/semtag`。

其他平台约束：

- 纯脚本包，`package_id` 删除 `arch`/`compiler`/`build_type`，保留 `os`。
- HMDFS 上 `chmod` 常被忽略、执行位不可靠：配方尽力 `chmod 0755`，test_package 一律通过
  显式解释器调用。
- 上游 0.2.0 脚本内嵌版本串为 `v0.1.2`（`semtag --version` 输出 `semtag: v0.1.2`），
  属上游发布瑕疵，不是适配问题，未修改。
- 上游 0.2.0 在工作区有未提交改动时执行 `getcurrent` 会因 `set -e` 与
  `status=$(check_git_status)` 的组合静默退出（退出码 1，无输出），属上游缺陷，未修改。

## 测试

| 来源 | 用例数 | 结果 |
|------|--------|------|
| 上游测试 | 0 | 源码包不含任何测试（清点证据见 `test_package/MANIFEST.yml`） |
| `test_package/test_semtag.sh` | 19 断言 | 19/19 通过 |
| `test_package/test_semtag_ohos.sh` | 5 断言 | 5/5 通过（hnp bash 缺失时相应断言报 SKIP） |

## 版本

| 版本 | 制品引用 | 上游版本 | 状态 |
|------|----------|----------|------|
| 0.2.0 | `semtag/0.2.0` | v0.2.0 | built |
