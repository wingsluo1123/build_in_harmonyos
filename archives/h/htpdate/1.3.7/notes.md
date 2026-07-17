# htpdate 1.3.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

htpdate 是一个简单的 C 程序，使用 Makefile 构建，无需 configure 步骤。

1. 下载源码：从 GitHub 下载 v1.3.7 tag
2. 解压到 builds 目录
3. 使用 make CC=clang CFLAGS="-Wall -std=c11 -pedantic -O2" 编译
4. 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | adjtime 函数不存在 | OpenHarmony 使用 adjtimex 替代 adjtime | 编译期特性检测：检测 adjtime 可用性，不可用时定义 ADJTIME_MISSING，使用 adjtimex_compat 替代 |
| 2 | install 命令不存在 | toybox 环境缺少 GNU install | 使用 cp + chmod 手动安装 |

## 源码修改

### 补丁 0001-htpdate.c.patch

通过编译期特性检测（非平台宏）判断 adjtime 是否可用。conanfile.py 在 build() 中尝试编译调用 adjtime 的测试程序，若失败则传入 -DADJTIME_MISSING。

```diff
+/* Fallback for platforms missing adjtime (uses adjtimex instead) */
+#ifdef ADJTIME_MISSING
+#define adjtime(tv, oldtv) adjtimex_compat(tv, oldtv)
+static inline int adjtimex_compat(const struct timeval *tv, struct timeval *oldtv) {
+    if (oldtv) {
+        struct timex cur = {0};
+        adjtimex(&cur);
+        oldtv->tv_sec = cur.offset / 1000000;
+        oldtv->tv_usec = cur.offset % 1000000;
+    }
+    struct timex txc = {0};
+    txc.modes = ADJ_OFFSET_SINGLESHOT;
+    txc.offset = (long long)tv->tv_sec * 1000000LL + tv->tv_usec;
+    return adjtimex(&txc);
+}
+#endif
```

## 依赖版本

无外部依赖，仅需标准 C 库。

## 验证结果

```bash
$ htpdate -v
htpdate version 1.3.7
```

## 注意事项

1. htpdate 可选择编译 HTTPS 支持版本（make https），需要 libssl
2. 编译期特性检测自动判断是否需要 adjtimex 兼容性补丁
3. 运行时需要 root 权限才能调整系统时间

---
**编译结束**: 2026-07-15
**最终状态**: built
