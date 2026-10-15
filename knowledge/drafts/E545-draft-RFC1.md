# E545 — bash 脚本把 /tmp 写死不止一处：只改 workdir 赋值会漏掉 --keep 分支

## 错误特征
```
Error: Failed to create temporary directory '/tmp/rfcdiff-12345'.
...
tar: rfcdiff-12345: Cannot open: No such file or directory      # --keep 分支
```
前者是未打补丁的主路径（E002 已覆盖），后者只在「已把 workdir 改到 `$TMPDIR` 但漏改 `cd /tmp`」时出现。

## 触发条件
- 构建系统: 无（单文件 shell 工具包，如 rfcdiff 1.49）
- 阶段: runtime（test_package 消费者用例 / 用户实际使用）

## 根因分析
鸿蒙 `/tmp` 只读（E002）。rfcdiff 同时有两处 `/tmp` 字面量：`workdir="/tmp/$basename-$$"`，以及保留现场分支里的
`cd /tmp; tar czf $basename-$$.tgz $basename-$$`。后者用相对路径打包，依赖「cwd == workdir 的父目录」。
只把第一处改成 `${TMPDIR:-/tmp}/…` 后，`--keep` 仍 `cd /tmp`，目录找不到（或写 tgz 到只读目录）失败。
主路径用例全绿，所以只测主路径会漏掉这个分支。

## 解决方案

### 推荐方案
1. `grep -n '/tmp' <script>`，逐处归类（工作目录赋值 / 后续 cd / 后续 tar、mv）。
2. `workdir="${TMPDIR:-/tmp}/$basename-$$"`；依赖该目录的 `cd /tmp` 改为 `cd "${workdir%/*}"`。
3. 保持 `$TMPDIR` 显式设置时的原有语义：目录不可用就报错，不要悄悄回退到 `/tmp`。

### 禁止做法
- ❌ 只改一处赋值就宣布 `/tmp` 已适配。
- ❌ 用软链 / 挂载改造构建机的 `/tmp` 来绕过只读（污染共享环境，CI 与用户设备不可复现）。

## 验证
```bash
grep -n '/tmp' <script>        # 不应再有独立的 /tmp 字面量（默认值 ${TMPDIR:-/tmp} 除外）
TMPDIR=$PWD/t bash <script> --keep a b   # 输出里的 "left in" 路径必须以 $PWD/t 开头，tgz 同目录存在
TMPDIR=$PWD/nope bash <script> a b       # 必须报错，而不是回退 /tmp 成功
```
rfcdiff 1.49 的 `test_package/test_rfcdiff_ohos.sh` 用例 3、5 即此验证；对未打补丁脚本跑这两条会失败。

## 关联条目
- 相关: E002（/tmp 只读总则）、E482（zsh heredoc 的 $TMPPREFIX）、E165（shebang）
