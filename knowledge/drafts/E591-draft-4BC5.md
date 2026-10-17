# E591 — OHOS musl 未导出 pthread_setcanceltype 导致运行期 relocating 失败

## 错误特征

程序在 OHOS(aarch64) 上编译链接**全部成功**（甚至 `conan create` 打包成功），但执行时
任何一次调用都以 rc=127 立即失败，stderr 形如：

```
Error relocating /path/to/exe: pthread_setcanceltype: symbol not found
```

（多条缺失符号按行输出；BIND_NOW 在进程启动前即完成全部重定位，因此没有 main() 中的任何输出。）

典型触发组合：

1. 目标代码调用了 POSIX 线程取消 API（本例：`src/cache.c` 的缓存回收线程
   `pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, NULL);`
   + `pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);`）；
2. 配方为避免另一批 libc 符号缺失，使用了
   `-Wl,--unresolved-symbols=ignore-all`（FUSE/musl 生态常见，如 libfuse.a 引用
   `pthread_cancel`/`pthread_setcancelstate` 时）；
3. 该开关使链接期不再报错，缺符号被推迟到运行期动态加载器解析 → 失败。

## 触发条件

* 平台：OpenHarmony / HarmonyOS（musl libc）
* 现象门槛：被调用符号**不在** libc 的动态符号表导出集合中
* 检测前提：目标 libc 只导出了部分同类 API

## 根因

OHOS musl libc 的动态符号表只导出 `pthread_cancel`(`T`)、`pthread_setcancelstate`(`W`)，
**未导出 `pthread_setcanceltype`**（可用 `nm -D --defined-only /system/lib64/libc.so` 核实）。
musl 内部确实实现了线程取消类型切换，但未作为公开动态符号提供，因此：

* 链接期：`ld.lld` 找不到定义（通常被 `--unresolved-symbols=ignore-all` 掩盖）；
* 运行期：动态加载器在 `.dynsym` 中看到未定义强符号且无处解析 → 拒绝加载（rc=127）。

与 E085（musl 缺 `pthread_cancel` 类 API 导致链接期 `undefined symbol` 或
`PTHREAD_IN_USE_DETECTION` 检测失败）同属 musl 线程 API 缺口，但**阶段与处置不同**：
E085 发生在链接期/configure 期，靠宏切换检测策略；本条目发生在**运行期重定位**，
需要真实提供符号定义。与 E531（musl 缺 `qsort_r` → 本地 compat shim）同族，
区别在于本条目必须与 `--unresolved-symbols=ignore-all` 的正则组合诊断，
且修复物以「随可执行文件静态链入的目标文件」形式交付。

## 推荐方案

**在 conan 配方内生成 libc 兼容层，并随可执行文件静态链入**（不改上游源码）：

1. `generate()` 中写出兼容实现并编译为 `.o`（编译器从 `tools.build:compiler_executables`
   取得，遵守 R33，不裸用 shell 变量）：

```c
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>

static __thread int wdfs_cancel_type = PTHREAD_CANCEL_DEFERRED;

int pthread_setcanceltype(int type, int *oldtype)
{
    if (type != PTHREAD_CANCEL_DEFERRED &&
        type != PTHREAD_CANCEL_ASYNCHRONOUS)
        return EINVAL;
    if (oldtype != NULL)
        *oldtype = wdfs_cancel_type;
    wdfs_cancel_type = type;
    return 0;
}
```

2. 用 `env.append("LDFLAGS", <obj>)` 把该目标文件加入链接行。显式目标文件不受
   链接顺序限制（不同于静态库），即使出现在 `LDFLAGS`（先于 objects）也能被全体
   目标文件解析。

**语义边界（必须在 PR/notes 如实声明）**：无法写回 libc 内部取消类型状态，
本平台取消类型保持缺省 `PTHREAD_CANCEL_DEFERRED`；取消仍由
`pthread_setcancelstate` 使能，并在下一个取消点（本例缓存线程的 `sleep()`）
生效，退出时 `pthread_cancel`+`pthread_join` 仍可终止线程。

## 验证方式

```bash
# 1) 动态符号表中不再残留未定义引用（修复后由链入的目标文件解析，
#    通常也不再作为导出符号出现在 .dynsym）
nm -D -u <pkg>/bin/<exe> | grep -c pthread_setcanceltype          # 期望：0

# 2) 运行期不再报错（须带依赖包运行环境；静态依赖无需，共享依赖如 glib 需 LD_LIBRARY_PATH）
LD_LIBRARY_PATH=<deps>/lib <pkg>/bin/<exe> --version              # 期望 rc=0
```

实测（wdfs 1.4.2，`$HOME/.conan2/p/b/wdfsbf7e1c2ef76c6/p/bin/wdfs`）：

```
$ nm -D -u <bin> | grep -c pthread_setcanceltype      → 0
$ LD_LIBRARY_PATH=...glib/lib:...expat/lib <bin> --version
wdfs version: 1.4.2                                    → rc=0
$ <bin>                                                → rc=1 "missing webdav uri"（参数校验分支正常）
```

修复前同一二进制为 rc=127 且 stderr 只有 `Error relocating ...: pthread_setcanceltype: symbol not found`。

## 适用边界

* 适用于任何在 OHOS/musl 上调用 libc 未导出 API 的 C/C++ 目标，尤其是
  「已用 `--unresolved-symbols=ignore-all` 掩盖链接错误」的项目。
* 仅当该 API 在业务路径中**非关键**（本例仅用于优化取消及时性）时可这样降级；
  若业务正确性依赖其语义，需改为源码层条件编译并暴露能力宏。

## 不适用边界

* 不要用 `#pragma weak`/弱符号声明绕过：musl 加载器仍会对强引用做重定位并要求定义。
* 不要把 `--unresolved-symbols=ignore-all` 当修复：它只隐藏链接期错误，正是本问题的
  漏检根因（单独使用会把缺符号推迟到运行期）。
* 不要用 `LD_PRELOAD`/dlopen 预加载：制品分发场景引入部署依赖，且与 conan 包
  「自包含」原则冲突。
* 多线程业务若依赖异步取消的即时性，兼容层不满足语义要求，应改源码实现。

## 关联条目

* `similar_to`: E078（musl BIND_NOW / dlopen 场景的 `Error relocating` 同族症状）、
  E085（musl 缺 pthread 取消 API：链接期/检测期处置）、
  E531（musl 缺 API → 本地 compat shim 方法论）

## 六维查重结论（main 分支 graph/doc/drafts 全量检索 + draft-review 复核）

工具预审建议 `merge-into E078`（score=0.56，sig=0.8 / kw=0.06 / cat=0.75），
人工逐维比对后判定为**部分重复后保留**（新增诊断、方案与边界）：

| 维度 | E078 | E509 | E085 | E531 | 本条 E591 |
|------|------|------|------|------|-----------|
| 触发条件 | dlopen 解释型扩展（Python 扩展模块），动态库版本/加载方式导致符号缺失 | harmonybrew 工具链二进制 RUNPATH 与系统旧版 OpenSSL 冲突 | 源码调用 `pthread_cancel` 等，链接期或在 `#pragma weak` 检测处失败 | 源码调用 glibc 扩展 `qsort_r`，链接期 undefined reference | 源码调用 **libc 未导出**的 `pthread_setcanceltype`；配方已用 `-Wl,--unresolved-symbols=ignore-all` |
| 错误特征 | `Error relocating <so>: <py api>: symbol not found` | `Error relocating cargo.real: symbol not found` | `undefined reference to pthread_cancel` / `PTHREAD_IN_USE_DETECTION` 失败 | `undefined reference to qsort_r` | `Error relocating <exe>: pthread_setcanceltype: symbol not found`（rc=127，链接与打包均成功） |
| 阶段 | runtime（dlopen 时） | runtime（加载器路径选择） | linking / configuration | linking | runtime（BIND_NOW 启动前重定位） |
| 根因 | 加载器 BIND_NOW 与扩展模块符号供给方式冲突 | 加载器优先用系统旧版 libssl | musl 未实现/未提供该 API，检测宏失败 | musl 的 BSD `qsort_r` 签名与 glibc 不兼容 | libc **未导出**该符号，且 `ignore-all` 把错误从链接期推迟到运行期被掩盖 |
| 解决方案 | 调整链接/加载策略（BIND_LAZY 等） | `LD_LIBRARY_PATH` 指向匹配版本 | 定义 `PTHREAD_IN_USE_DETECTION_HARD` 切换检测方式 | 源码内注入 libc 兼容实现 | 配方内生成兼容层 `.o` 并经 `LDFLAGS` 链入（不改上游源码） |
| 不适用边界 | 不适用于静态/非 dlopen 场景 | 不适用于静态链接场景 | 不解决"运行期重定位缺符号" | 不涉及 `ignore-all` 掩盖链 | 不适用于依赖异步取消即时性的业务；禁用弱符号/`LD_PRELOAD` 绕行 |

**重合点**：症状文本同族（`Error relocating …: <symbol>: symbol not found`）且都与 musl 动态加载语义相关；
**差异点**：本条根因是「libc 未导出符号」+「`ignore-all` 掩盖链接错误」的组合，E078/E509 分别是加载方式与库版本选择，
E085/E531 都发生在链接期；**新增价值**：给出「用 `nm -D --defined-only /system/lib64/libc.so` 比对导出集合」这一诊断法，
给出 `LDFLAGS` 注入显式目标文件（不受链接顺序限制）这一配方级修复范式，并明确三条禁用绕行方案。

查重证据：`grep -rl "setcanceltype\|Error relocating" knowledge/graph knowledge/doc knowledge/drafts`（命中
E078/E085/E127/E142/E176/E186/E274/E286/E316/E501/E505/E509/E513/E520 等，逐条比对后无同根因条目）；
`ohc-run.py draft-review E591-draft-4BC5`（预审通过 signature/root_cause/rec 三项质量预检）。
