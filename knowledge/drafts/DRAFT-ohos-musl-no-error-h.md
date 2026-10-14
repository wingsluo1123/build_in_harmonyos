# DRAFT-ohos-musl-no-error-h — musl 无 <error.h>，glibc error()/error_at_line() 上游代码编译失败

> 对应结构化数据：`knowledge/drafts/DRAFT-ohos-musl-no-error-h.kv`
> Contributor: Ember5843 / Status: DRAFT / Updated: 2026-09-27 / Severity: 2
> 触发事件：libdebuginfod/0.195 HarmonyOS PC 适配（PR #12349）
> 注：原 DRAFT-13121-* 草稿文件丢失（worktree 清理时未落库），本条为依据 libdebuginfod
> 配方与 notes 实测记录重建。

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目的增量（差异化） |
|---|---|---|---|
| DRAFT-ohos-musl-glibc-specific-symbols | 草稿 | glibc 特有**符号/变量**（program_invocation_short_name、__progname）缺失 | 本条是 glibc 特有**头文件 + 函数族**（error.h 的 error/error_at_line），需要可打印格式化错误并 exit 的完整 shim 实现，非单符号替换 |
| DRAFT-argp-musl-gap-bridge | 草稿 | argp 解析族缺失 → bridge 库 | 同为"glibc 便利设施 musl 缺失"，但本条规模小，单头文件 shim 即可，无需独立 bridge 包 |
| DRAFT-rjj666-libmysofa-musl-pthread-cancel-flag-join | 草稿 | pthread_cancel 语义差异（flag+join 替代） | 平行的 glibcism，单独成条；本条不覆盖线程取消 |

## Scope（何时用）

- **触发特征**：编译上游工具/测试程序时报 `fatal error: error.h: No such file or
  directory`，或链接期 `undefined reference to 'error'/'error_at_line'`；源码里
  `#include <error.h>` 且调用 `error(status, errnum, fmt, ...)` /
  `error_at_line(status, errnum, file, line, fmt, ...)`。autotools 项目常表现为
  configure 探测 `error.h` 失败后 AM_CONDITIONAL 关掉部分程序，或直接编译炸。
- **典型实例**：elfutils/libdebuginfod 0.195 的测试程序与工具源码大量使用
  error()/error_at_line()（glibc 习惯）。

## Symptom（真实报错形态）

```
debuginfod.cxx:42:10: fatal error: 'error.h' file not found
#include <error.h>
         ^~~~~~~~~
```

或上游 Makefile 干脆把用 error.h 的程序排除出 EXTRA_PROGRAMS，导致**上游测试面静默
缩水**——这会连锁触发审核 rule2/3（测试减少）追问。

## Root Cause

`<error.h>` 及 error()/error_at_line()/error_message_count/error_status 是 **glibc
扩展**，POSIX 未定义；musl libc 不提供该头文件。上游代码按 glibc 惯例直接 include，
在 OHOS（musl）上编译失败或被构建系统剔除。

## Recommended Solution（主方案 + 回退）

**主方案（shim 头注入，libdebuginfod 0.195 先例）**：

1. 配方 `generate()` 写出 shim 目录，内含 `error.h`：用 stdarg 实现
   glibc 兼容的 `error()`/`error_at_line()`（vfprintf 到 stderr、附 program_invocation
   信息可省略、按 status 非零 exit、维护 error_message_count）。
2. `build_context` 的编译 flags 最**前置** `-I<shimdir>`，保证上游
   `#include <error.h>` 命中 shim 而非系统路径：
   `self.build_context_info.cpp_flags = f"-I{shimdir} " + 原flags`（或注入
   CXXFLAGS/CFLAGS 环境变量）。
3. test_package/MANIFEST 如实声明：上游测试程序因此可用，测试面**不缩水**。

**回退方案（剔除法）**：shim 不可行时（如 C++ 模板重载冲突），patch Makefile.am.in
剔除使用 error.h 的非核心测试程序，并在 PR 描述按 §8.6 逐条归因——核心业务面必须
保留真实执行，不许整体跳过。

⚠️ 禁止笼统写"平台不支持 error.h"就砍测试——审核 rule2/3 不接受资源/平台笼统理由。

## 单库实证

| 库 | 角色 | 结果 |
|---|---|---|
| libdebuginfod/0.195（PR #12349） | generate() 注入 error.h shim + 前置 -I | 上游测试程序全部可编译执行，PR 已合入 |

## 测试覆盖边界

- 声明通过率口径：以 PR #12349 实测为准（上游测试按上游 CI 口径真机执行）。
- 差异定位表逐条核验：与 glibc-specific-symbols（单符号）、argp（bridge 包）、
  pthread-cancel（线程取消）非重复申报。

## 遗留事项

- 原 DRAFT-13121 文件丢失，本条重建后若找回原文件以原文件为准合并。
- 若后续多个库都需要 error.h + 其它 glibcism shim，可评估合并成共享 bridge 包
  （argp-musl-gap-bridge 模式），当前单头文件 shim 足够、不必引包。
