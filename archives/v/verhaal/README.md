# verhaal

Linux stable 分支提交解析与查询工具（upstream tag `v025`）。

verhaal 扫描 Linux 内核 stable 树，把所有 stable 分支提交（含 `Fixes:` 尾行构成的
修复关系图）建进一个 SQLite 数据库 `verhaal.db`，从而可以反查：

- 某个 mainline 提交被回填（backport）到了哪些发行版；
- 某个提交修复了哪个提交；
- 各发行版区间之间新增了哪些提交。

上游以此支撑内核 CVE 团队（`vulns.git`）的 CVE 追踪流程。

- 上游仓库: https://git.sr.ht/~gregkh/verhaal
- 许可: GPL-2.0-only
- 构建系统: meson

## 用法

```sh
export CVEKERNELTREE=/path/to/linux-stable-git-tree   # 必须是本地内核 git 仓库
verhaal                                               # 生成 verhaal.db
verhaal --database=/path/to/other.db                  # 指定库文件
verhaal --verbose                                     # 调试输出
verhaal --fixes                                       # 把非法 Fixes: 行打到 stderr
```

> 仓库需具备本地 `master` 分支（作为 mainline 基准）与**附注**发行标签
> （verhaal 用 `git describe` 取版本，轻量标签会失败）。

## HarmonyOS PC 适配

| 项 | 说明 |
|----|------|
| 目标平台 | HarmonyOS PC / OpenHarmony aarch64（`ci/conan/profiles/ohos-aarch64`） |
| 依赖 | libgit2 1.9.0、sqlite3 3.53.4、pcre2 10.45（均静态链入，产物仅依赖 libc） |
| 补丁 | `025/patches/0001-src-main.c.patch`：HMDFS 共享属主下 libgit2 属主校验恒失败，打开失败时关闭校验重试（详见 `025/notes.md`） |
| 消费者测试 | `025/test_package/test.sh`（4 项：版本 + 建库 + 回填查询语义） |
| 鸿蒙真机测试 | `025/test_ohos/run_ohos_test.sh`（7 项，含补丁回归） |

## 版本索引

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|----------|------|
| 025 | built | 2026-10-15 | 首次适配（含 HMDFS 属主校验补丁）；PR 阶段状态，合并后由发布流水线 upload 转 published |
