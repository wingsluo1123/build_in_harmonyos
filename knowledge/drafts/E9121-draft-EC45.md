# E9121 — HarmonyOS PC /tmp 为只读挂载：硬编码 /tmp 的 scratch 文件目录使程序完全不可用

## 错误特征

程序启动即报 scratch/临时文件创建失败，且在任何用户命令被执行之前就以非零码退出：

```
$ printf ',p\nq\n' | ed -s file
/tmp/ed.XXXXXXXXXX: Read-only file system
$ echo $?
2
```

同类症状：`cannot open temp file`、`mkstemp: Read-only file system`、
`failed to create temporary file`。

## 触发条件

- 构建系统: custom（上游为手写 POSIX sh `configure` + 纯 Makefile，非 autoconf）
- 阶段: 运行时（程序启动、第一条命令之前）；在 G0 干净构建后的运行验证阶段暴露
- 平台: HarmonyOS PC（`/proc/mounts` 中 `/dev/block/dm-0 /tmp erofs ro,...`）

## 根因分析

HarmonyOS PC 的 `/tmp` 是 **erofs 只读挂载**，`/var/tmp`、`/dev/shm`、
`/data/local/tmp` 同样不可写；`TMPDIR` 平台默认不存在（仅当用户在 shell 配置里显式导出）。

上游 oed 的 `buf.c` 把 scratch 文件模板**编译期写死**为 `"/tmp/ed.XXXXXXXXXX"`，而
`main.c:192` 的 `init_buffers()` 在启动时**无条件**调用 `open_sbuf()`（上游原始源码调用点
`buf.c:272`），
`mkstemp()` 必然失败 —— 结果是工具完全不可用（不是"某个功能不可用"），因为 scratch
文件承载行缓冲与撤销语义。

## 解决方案

### 推荐方案

1. 把编译期常量拆成目录与模板名两部分（`SCRATCH_DIR` 默认 `/tmp` + `SCRATCH_NAME`）；
2. 路径缓冲由 `sizeof(SCRATCH_TEMPLATE)+1` 放大为 `PATH_MAX`；
3. `open_sbuf()` 改为遍历候选目录 **`$TMPDIR` → 编译期内置目录 → `$HOME`**，
   第一个 `mkstemp()` 成功的即采用；
4. **不使用任何平台宏**：`/tmp` 可写的系统（Linux/macOS）第一次尝试即成功，行为与上游
   逐字一致，仅当内置目录不可写时才启用回退。

参考实现：`archives/o/oed/7.4/patches/0001-buf.c.patch`。

### 禁止做法

- ❌ 用 `#ifdef __OHOS__` 之类平台宏把路径换成另一个硬编码值 —— 污染上游且其它平台无法受益；
- ❌ 直接删掉 scratch 文件机制 —— ed 的行缓冲/撤销语义依赖它，会引入数据丢失；
- ❌ 仅在文档里让用户"自己设 TMPDIR" —— 开箱不可用不满足适配要求。

## 验证

```bash
# 设 TMPDIR（可写）
printf 'a\nx\n.\nw f\nq\n' | TMPDIR=$HOME/tmp ed -s f && cat f
# 不设 TMPDIR：经 $HOME 回退仍应成功（鸿蒙）
printf 'a\ny\n.\nw g\nq\n' | ed -s g && cat g
```

## 关联条目

- 相关: E9122
