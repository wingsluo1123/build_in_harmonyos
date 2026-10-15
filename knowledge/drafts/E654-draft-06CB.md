# E654（草稿）— gawk 专有函数即使有运行期保护，也会让无该函数的 awk 在解析阶段整体失败

> 草稿（DRAFT）— 来自 cascade 1.4 HarmonyOS PC (aarch64) 适配，PR !14708 第一轮 CI 的真实失败。与 `.kv` 配对。

## 错误特征

OHOS CI（`conan create` 内 test_package）日志：

```
PASS: --version prints 'cascade 1.4'
FAIL: ex1.cas runs to completion (exit 0)
awk: file (cmdline) line 0: Undefined function 'strftime'
awk: 1 syntax error(s)
...
cascade consumer test: 11 passed, 13 failed
```

`--version`、`--help`、缺失输入文件等在 sh 层处理的路径仍然通过；凡是进入 awk 的运行全部失败。

## 触发条件

- 项目类型：sh 脚本内嵌 awk 程序（`$AWK ' ... ' file`）
- 阶段：运行期（也是 test_package 阶段）
- 目标机 awk 没有 `strftime`；本机 awk（mawk 1.3.4 20250131 / gawk）有

## 根因分析

cascade.sh 的 awk 程序末尾：

```awk
if(ARGV[0] == "gawk"){
  now = strftime("%a %b %d %H:%M:%S %Z %Y")
  printf("*            %28s                  *\n",now)
}
```

awk 在执行前整体解析程序，函数调用在**解析阶段**就必须解析到已定义函数或内建函数。运行期条件保护不了解析：
没有 strftime 的 awk 直接拒绝整个程序。本地 `conan create` 用的 mawk 内置 strftime，所以 24/24 全绿，
远程 CI 才暴露（本地绿、CI 红）。CI 的 awk 具体是哪个实现未确认，未能在本机复现其解析错误。

## 解决方案

### 推荐方案

`patches/0001-cascade-drop-gawk-strftime.patch` 删掉该块（仅 gawk 下多打一行时间戳，无功能损失）。
补丁是通用可移植性修复，不含 `__OHOS__`。`test_package` 对 ex1 运行断言 stderr 为空，使同类解析错误不会被部分输出掩盖。

### 回退方案

确需时间戳：改成按 awk 实现拆分的两份程序，或自定义函数；gawk 下重定义内建函数名是语法错误，所以不能直接 shim。

### 禁止做法

- ❌ 用 `ARGV[0]=="gawk"` 之类运行期判断来“规避”gawk 专有函数——解析阶段已失败。
- ❌ 给配方加 gawk 依赖：包运行时用的是目标机 awk，不是构建时的 gawk。

## 验证

```bash
grep -nE 'strftime|systime|mktime|gensub|asorti?|PROCINFO|BEGINFILE|@include' cascade.sh
cascade examples/ex1.cas 2>err.txt >out.txt; test ! -s err.txt && diff out.txt examples/ex1.out
# 以远程 CI（OHOS 构建机）的 test_package 结果为准
```

## 关联条目

- 无直接相近条目（`strftime` 在正式条目与草稿中无同类命中；E550 的 `strftime %F` 是 C 库格式串，不同问题）。
- 同一 PR 的另一草稿：E653-draft-D418（nroff 缺失）。
