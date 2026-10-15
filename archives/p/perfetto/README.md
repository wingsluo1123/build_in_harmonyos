# Perfetto（HarmonyOS PC 适配）

Perfetto 是一套系统级**性能追踪与 trace 分析**平台：内核/用户态采集服务（`traced`/`traced_probes`）、
客户端追踪 SDK（`libperfetto`）、命令行工具（`perfetto`）、以及离线分析引擎
**trace_processor**（把 trace 当作 SQL 数据库查询，配套 `trace_processor_shell` 交互式 shell）。

## 功能概述

- **trace_processor**：trace 的 SQL 分析引擎（`trace_processor_shell`、`trace_processor` 库、diff/SQL 套件）
- **traced / traced_probes**：追踪守护进程与探针（ftrace 等）
- **perfetto CLI**：命令行采集工具（`perfetto`、`tracebox`、`traceconv`）
- **追踪 SDK**：`libperfetto.so` 与 `include/perfetto/**` 公共头，供应用嵌入埋点

## OHOS 适配要点

本库构建系统为 **GN + Ninja**（上游 standalone 构建），不是 CMake/autotools，适配要点：

1. **GN 工具链自举**：上游 `tools/gn` 只是下载器，不 vendor 二进制；预编译 gn 为 x86/glibc 且不带
   `.codesign`，在 OHOS aarch64 上无法执行。故用 **OHOS clang 从 gn 源码自举**（pin 上游
   `install-build-deps` 指定的同一 revision）。
2. **系统编译器**：`is_system_compiler=true` + `is_hermetic_clang=false`（上游为系统编译器保留的
   配置：不使用 `-Weverything`/`-Werror`，因为那是按其 hermetic clang 校准的）。
3. **清空交叉配置**：上游把 `linux/arm64` 当成"x64 主机交叉编 arm64"（默认 Debian sysroot），
   OHOS 上置 `target_triplet=""` + `sysroot=""`。
4. **保留签名**：OHOS 用户存储中的 ELF 需 `.codesign` 段才能执行，而 `strip` 会使其失效 →
   构建置 `strip=""`。
5. **第三方依赖**：上游的 20 个 `buildtools/` 源码包改由 GitHub 可达镜像供给（同一 commit SHA），
   全部 sha256 pin。唯一例外是 zlib（上游用不可得的 chromium 专有 fork）→ 改用 OHOS sysroot 自带
   系统 zlib。
6. **musl 差异补丁**：`qsort_r` / `fts.h` / `program_invocation_short_name` 缺失、
   `<linux/socket.h>` 重定义 `sockaddr_storage` —— 见 `58.2/patches/`。

## 依赖关系

- 编译依赖：OHOS clang 15（系统）、ninja（conan `tool_requires`）、python3、perfetto 自带 vendored 源
- 运行依赖：OHOS 系统 libc++ / libz 等系统库

## 参考资料

- 官网：https://perfetto.dev
- 源码：https://github.com/google/perfetto ｜ 文档：https://perfetto.dev/docs
- 适配笔记：`58.2/notes.md`
