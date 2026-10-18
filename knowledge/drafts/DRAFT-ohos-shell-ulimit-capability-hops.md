# DRAFT-ohos-shell-ulimit-capability-hops：OHOS 各 shell 的 ulimit 能力差异——mksh 静默 no-op，提栈必须在每个 exec 跳板用能力验证过的 shell 落地

> Source: xlispstat 3.52.23 真机适配 r14–r25（<真机IP>:<端口>，HarmonyOS PC aarch64）
> 对应 KV: knowledge/drafts/DRAFT-ohos-shell-ulimit-capability-hops.kv
> Draft only. 不修改 knowledge/graph/、doc/、索引与运维规则。

## 一句话

OHOS 设备上 `/system/bin/sh`(mksh) 的 `ulimit -s` 是**静默 no-op**（连查询都无输出、
rc=0、实际不生效），只有 hnp bash（`/data/service/hnp/bin/bash`）等完整 shell 的
`ulimit -s unlimited` 真正生效；因此"提升栈限制"这类修复**必须在每一个 exec 跳板**
（构建步骤脚本 → 已安装 wrapper → 消费者测试 harness）用**能力验证过的 shell**落地，
否则同一程序在一条链上不崩、在另一条链上必崩。

## 错误特征（真实日志）

解释器类/深递归程序在默认 8MB 栈下确定性 SIGSEGV（本例：xlisp 的 GC mark 阶段按
cons 单元递归，加载统计运行时 `stats.lsp` 时触发）：

```text
XLISP-PLUS version 3.04
Signal 11 (core dumped)
make[1]: *** [Makefile:14: compiler/backquot.fsl] Error 139
```

判别实验（同一二进制、同一输入，仅栈不同）：

```text
默认栈（mksh 环境）:        20/20 崩
ulimit -s unlimited 后:     10/10 通过（require stats 全过）
```

## 根因

1. OHOS 设备默认主线程栈 8MB，对老解释器的 C 级深递归（GC mark、编译器递归）不够；
2. `ulimit` 是**进程属性**，只能向子进程继承、不能事后修改——所以提栈动作必须发生在
   目标进程的**所有可能祖先**里；
3. mksh 的 ulimit 内建对 `-s` 不支持但**不报错**（`ulimit -s` 查询输出为空、rc=0、
   `ulimit -s unlimited 2>/dev/null` 也 rc=0），形成"已提栈"假象；hnp bash 的
   `ulimit -s` 查询返回 `8192`、`unlimited` 后再查为 `unlimited`，真正生效。

## 使用说明（可复制流程）

### ① 能力探测（在真实构建目录里测，不要凭 shell 种类推断）

```sh
# 对每个候选 shell：能查出数值且能改成 unlimited 的才算"有能力"
for sh in /system/bin/sh /data/service/hnp/bin/bash; do
  "$sh" -c 'ulimit -s' 2>/dev/null   # 有数值输出 → ulimit 可用
done
```

- mksh：`ulimit -s` 无输出 → 该 shell 内提栈无效；
- hnp bash：输出 `8192` → 可用。

### ② 提栈三跳板（缺一即复发）

```sh
# 跳板 1：构建步骤脚本（make 触发的 interpreter 运行）
ulimit -s unlimited 2>/dev/null || ulimit -s 65536 2>/dev/null || true
exec make -j1 ...

# 跳板 2：安装后的 wrapper（消费者/用户交互运行）
#!/system/bin/sh
...
ulimit -s unlimited 2>/dev/null || ulimit -s 65536 2>/dev/null || true
exec "${XLISP}" -w"${WKS}" "$@"

# 跳板 3：消费者测试 harness（test_package 脚本，本身跑在有能力的 shell 里）
ulimit -s unlimited 2>/dev/null || true
printf '(+ 1 2) (exit)\n' | "$XL" -w"$WKS" > "$out" 2>&1
```

注意：若 wrapper 的 shebang 是 mksh，wrapper 内的 `ulimit` 无效——此时要么由
harness（bash）先提栈再 exec wrapper，要么把 wrapper shebang 换成有能力的 shell
（需与"HMDFS 拒绝脚本 exec"的约束合看，见查重声明）。

### ③ 验证（不要只跑一次）

同一输入连跑 ≥10 次计崩/过（本例提栈前 20/20 崩、提栈后 10/10 过）。
管道捕获崩溃输出会丢缓冲（见"陷阱"），计数要基于**退出码**（139/非 0）而非输出文本。

## 陷阱

- **输出缓冲丢失**：`echo '...' | interp | grep` 时，SEGV 会丢掉 stdio 缓冲里未刷出
  的全部输出——"崩溃前没有打印标记"≠"没执行到标记"。用退出码计数，或让被测程序把
  进度写到文件。
- **插桩污染回滚**：给共享源文件（如 init.lsp）插桩后必须在同一脚本里恢复原文件；
  跨探针的 `.orig` 备份链一旦有一次恢复失败，后续所有探针都在测被污染的输入
  （本例实测：插桩版 init.lsp 被当作原件复测，得出"0/20 崩"的假阴性）。
- **mksh ulimit 假成功**：`ulimit -s unlimited 2>/dev/null || true` 在 mksh 下
  rc=0 但什么都没做——`|| true` 兜底会掩盖失效。

## 适用范围

- OHOS/HarmonyOS PC 真机上运行**深 C 递归**类程序：Lisp/Prolog/Smalltalk 解释器的
  GC 与求值、宏展开器、递归下降解析器、自举编译器；
- 任何需要提升 ulimit（栈/nofile/内存）的构建与消费者测试；
- 多 shell 环境（mksh + hnp bash 并存）下的限制类修复。

不适用：宿主 Linux（bash ulimit 正常）；与栈无关的确定性段错误（先按本文方法
把栈提满，若仍崩则另寻根因——本例中 compile-file 的 SEGV 与栈无关，真因是
无头图形桩，见查重声明）。

## 输入 / 输出

- 输入：崩溃二进制、其运行链（构建步骤/wrapper/harness）、候选 shell 列表；
- 输出：能力验证结论（哪个 shell 能提栈）+ 三跳板的提栈补丁 + ≥10 次重复的
  崩溃率前后对照。

## 示例（xlispstat 3.52.23 实测，2026-10-16）

- 提栈前：`echo '(exit)' | ./xlisp` 于 src/lsp（自动加载完整 init，含 stats.lsp）
  → Signal 11，20/20；
- 提栈后（hnp bash `ulimit -s unlimited`）：同输入 → 10/10 通过；
- 落地：conanfile.py 三个 make 步骤脚本 + 0001 补丁的 wrapper + test_package
  harness 各加一行提栈（commit 540d398b17）。

## 查重声明

- `DRAFT-gcc-snapshot-20260705-ohos-source-tree-and-fresh-build`（未提交，主仓
  knowledge/drafts）仅作为 GCC 自举的旁注提到 `ulimit -s unlimited`，未覆盖
  mksh 静默 no-op、能力探测、三跳板完整性、缓冲丢失陷阱；
- grep 全部 6587+3266 篇草稿（worktree + 主仓，含未提交），无 "ulimit 能力差异 /
  提栈跳板" 主线条目；
- HMDFS 脚本 exec 拒绝（`bad interpreter`）已由
  `DRAFT-cdb-20251021-hmdfs-shebang-script-exec-refusal` 覆盖，本条不重复；
  二者经常需要组合（wrapper 既要换 shebang 又要提栈）。
