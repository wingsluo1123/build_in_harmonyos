# E627 — 内核不支持 madvise(MADV_FREE)，上游断言终止进程

## 错误特征

- 进程在**启动早期**断言失败 / abort 退出，日志含 `madvise`、`EINVAL` 或 `errno 22`。
- 常见于名为 `*ForkBugCheck`、`*MemoryCheck` 之类的一次性内核能力探测。
- 换一台"支持 MADV_FREE 的内核"的机器上同一二进制可正常启动——环境相关性极强。

## 触发条件

- 构建系统: 任意（与构建系统无关）
- 阶段: runtime（启动早期的能力探测）
- 平台: 内核未实现 `MADV_FREE`（部分 OpenHarmony / HarmonyOS PC 构建内核）
- 上游特征: 探测函数把 `madvise(MADV_FREE)` 的返回值当作不可失败的前置条件

## 根因分析

`madvise(MADV_FREE)` 是**建议性**调用，内核可以不实现：不支持时返回 `-1` 且 `errno=EINVAL`。
上游却把它写成"必然成功"的探测前提，失败即 `serverAssert` / 终止进程。

语义上的错误在于：被探测的那个 arm64 fork bug **只存在于实现了 `MADV_FREE` 的内核上**。
内核对 `MADV_FREE` 返回 `EINVAL`，恰恰说明它**不受该 bug 影响**——
此时正确结论是"探测无法执行 → 视为不受影响"，而不是"致命错误"。

## 解决方案

### 推荐方案

把探测失败降级为"不受影响"，并记录警告：

```c
if (madvise(addr, len, MADV_FREE) != 0) {
    /* 内核未实现 MADV_FREE（多为 EINVAL）：被探测的 bug 仅存在于
       实现了 MADV_FREE 的内核上，故此处判定为不受影响 */
    serverLog(LL_WARNING,
        "madvise(MADV_FREE) unsupported (errno=%d); skipping fork-bug probe, "
        "assuming not affected", errno);
    return 0;   /* 不再 assert / 终止 */
}
```

### 禁止做法

- ❌ 保留 `serverAssert(madvise(...) == 0)` 之类的写法，或探测失败直接 `exit()`。
- ❌ 用"跳过整个启动期检查"当作修复——应保留探测、只改失败语义。

## 验证

真实的最小复现探针（在不支持 `MADV_FREE` 的核上，第三条应为 `-1/EINVAL`，第四条为 `0`）：

```c
void *p = mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
errno = 0; int a = madvise(p, 4096, MADV_FREE);
printf("MADV_FREE=%d errno=%d\n", a, errno);
errno = 0; int b = madvise(p, 4096, MADV_DONTNEED);
printf("MADV_DONTNEED=%d errno=%d\n", b, errno);
```

判定：`MADV_FREE` 返回 `-1` / `errno=22 (EINVAL)` 且 `MADV_DONTNEED` 返回 `0`
→ 确认内核对 `MADV_FREE` 无实现，而非调用方式有误。

修复后程序应正常启动，并在日志中出现一条 `MADV_FREE` 不受支持的警告。

## 关联条目

- 相关: E595（同为"平台能力缺失被当作必然可用"导致启动期崩溃）
