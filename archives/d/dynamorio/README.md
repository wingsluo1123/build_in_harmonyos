# dynamorio

动态二进制插桩（DBI）框架。DynamoRIO 在运行期重写应用程序代码、把生成的代码放入自有代码缓存，
并以碎片（fragment）为单位调度执行，从而支持指令级追踪、缓存模拟、覆盖率统计等客户端分析。
本仓库适配版本面向 **HarmonyOS PC（OHOS / aarch64 / musl / clang 15）**。

## 版本

| 版本 | 上游 | 说明 |
|---|---|---|
| `11.91.20676` | master @ 2026-08-11（commit `e2b756de…`） | 上游版本号末段 = commit 距 epoch 的天数；最近的两个 cronbuild tag 为 `cronbuild-11.91.20672` / `cronbuild-11.91.20679` |

源码 sha256：`b4b375236823590f3f02faa3f40446791f40e5efef89d33ea1759c52dcb60629`
（子模块 `third_party/elfutils` 单独获取：`0340ec69…`；`third_party/libipt` 为 x86 Intel-PT 专用，aarch64 不需要）

## 产物形态

- 库：`libdynamorio.so`、`libdynamorio_static.a`、`drdecode`/`drlibc`/`drmemfuncs` 等、`ext/lib64/release/libdrsyms.so`
- 工具：`drrun`、`drconfig`、`drinject`、`drloader`、`drnudgeunix`、`runstats`（见软件级 `commands.json`）
- CMake 包：`cmake/DynamoRIOConfig.cmake`（消费方可 `find_package(DynamoRIO)`）
- 客户端/工具：`drcachesim`（`drmemtrace`）、`drcov`、`drcpusim` 等

## 适配要点

见 `manifest.yaml` 的 `ohos_adaptation` 与版本目录下的 `notes.md`。核心四条：

1. **`SPLIT_SYMBOLS=OFF`**：OHOS 校验 ELF `.codesign`（长度须等于文件大小），链接后的 objcopy/strip 会破坏它。
2. **签名救援内建**：平台版 `ld.lld --code-sign` 在链接大型静态库时签名不一致 → 配方 `package()` 用
   `llvm-objcopy` + `binary-sign-tool -selfSign 1` 自动补签（`ohos_resign.py`）。
3. **seccomp 差异**：OHOS 对 `clone3` / `rseq` 发 SIGSYS 杀进程 → 对应探测在 OHOS 上跳过。
4. **musl 装载器差异**：不调 `DT_INIT`、不传 `argc/argv/envp` → `_init` 改挂 `.init_array`，环境自 `/proc/self/environ` 恢复。

## 消费者

```cmake
find_package(DynamoRIO REQUIRED)
add_executable(myapp myapp.c)
configure_DynamoRIO_standalone(myapp)   # 静态（standalone）形态，OHOS 上已验证可用
```

运行期注入（`drrun`）形态在 OHOS 上的现状见 `notes.md` §5「需评审委员会确认的问题」。
