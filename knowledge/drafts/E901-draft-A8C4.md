# E901-draft-A8C4 — Bash 工具上游 `set -e` + `x=$(fn)` 静默 rc=1：先判定为上游行为，不打补丁，测试断言退出码与副作用

> 草稿，来源 semtag 0.2.0 适配。待主编审核后 promote。

## 错误特征

- 脚本类包（纯 Bash 工具）的某条子命令执行后 **没有任何输出、退出码 1**，没有 `ERROR:` 提示。
- 在 test_package 里表现为 `rc=1 out=''`。
- semtag 0.2.0 实例：在工作区有未提交改动的 Git 仓库里执行 `semtag getcurrent`，或不带 `-f` 执行 `semtag alpha|beta|candidate`，静默退出 1（`final` 在脏树上先被 `git diff master` 检查拦下，报 ERROR，不属于静默）。

## 触发条件

- 构建系统: custom（单文件 Bash 脚本）
- 阶段: testing / runtime（设计 test_package 断言时发现）
- 脚本带 `set -e`（或 `set -euo pipefail`），并写有 `var=$(func)`，其中 `func` 以非零返回码表达「状态」。

## 根因分析

semtag 的 `check_git_status` 在有改动时 `echo "unstaged"; return 1`，调用处是
`status=$(check_git_status)`，紧接着本来要 `if [[ "$status" != "clean" ]]; then error "Repository has $status changes. Use -f to force."`。
errexit 下赋值语句的退出状态等于命令替换的退出状态，非零即令脚本立刻退出，`if` 与 `error` 永远走不到，所以既没有提示也没有后续行为。

这与鸿蒙无关：在 Debian bash 5.2.37 上复现完全一致。容易被误判为「鸿蒙 bash / toybox 与 GNU 工具行为不同」，从而去写不必要的平台补丁。

## 解决方案

### 推荐方案

1. 先在 x86 参照机用最小复现判定是否为上游行为：
   `bash -c 'set -euo pipefail; f(){ echo dirty; return 1; }; s=$(f); echo unreachable'; echo "rc=$?"`
   （rc=1、无 `unreachable`）。与鸿蒙症状一致即判为上游行为。
2. **不写补丁**，保持 `patches/` 只含真正的平台适配（semtag 只有一处 shebang）。
3. notes.md「遇到的问题」表登记根因与最小复现；README 平台约束节如实写明。
4. test_package 只断言 **退出码非 0 + 没有副作用**（semtag：脏树时不创建 tag），不断言输出文本，避免把缺陷固化成期望值。

### 回退方案

只有该缺陷让安装后的工具在鸿蒙上完全不可用时，才补丁：`status=$(check_git_status) || true`。补丁要写进 `conandata.yml`，notes 注明「上游缺陷修复，非平台适配」，且不得带 `__OHOS__` 宏。

### 禁止做法

- ❌ 把静默退出当作鸿蒙 bash 缺陷，用 `__OHOS__` 平台宏打补丁。
- ❌ 在测试里断言 `rc=1 out=''`，把上游缺陷当期望行为。

## 验证

```bash
bash -c 'set -euo pipefail; f(){ echo dirty; return 1; }; s=$(f); echo "unreachable: $s"'; echo "rc=$?"
# rc=1，且不打印 unreachable
bash -c 'set -euo pipefail; f(){ echo dirty; return 1; }; s=$(f) || true; echo "reached: $s"'; echo "rc=$?"
# reached: dirty，rc=0
```

semtag 实证（x86，bash 5.2.37 / git 2.47.3）：

```
$ semtag getcurrent        # 干净树 -> v1.2.4, rc=0
$ printf c >> f; semtag getcurrent   # 脏树 -> 无输出, rc=1
$ semtag alpha             # 脏树、无 -f -> 无输出, rc=1, 无新 tag
$ semtag alpha -f          # -> v1.2.5-alpha.1, rc=0
```

## 关联条目

- 相近: E275（`set -e` 下 `grep -v` 返回 1 被当失败——同属 errexit 误伤，但那是管道/过滤返回码，本条是命令替换赋值语句的退出状态）、E037（鸿蒙无 /usr/bin/env，shebang 改写——本包唯一的真平台补丁）、E165
- 区别: E037/E165 是「平台缺失导致无法执行」，本条是「上游脚本语义缺陷被误读为平台差异」，处置原则相反：不补丁、只调整测试断言。
