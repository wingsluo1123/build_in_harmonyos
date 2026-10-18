# DRAFT-imv-5.0.1-pthread-cancel-ohos-nonRT-signal-shim: OHOS 线程取消三层缺失下用非 RT 信号保住 cancel→join 语义

- 条目主题：OHOS（musl 系）对 POSIX 线程取消 API **三层同时缺失**（SDK 头不声明 + 动态桩
  libc.so 不导出 + 运行时导出却返回 ENOSYS 的空壳）。当上游**真依赖取消来解除阻塞**
  （取消阻塞在 read/poll 的工作线程，随后 join）时，压链接或写 `return 0` 空实现都会
  把链接错误升级成**静默挂起**；正确解法是零上游补丁的兼容 TU：用**非 RT 信号 SIGUSR1**
  装 handler，handler 内 `pthread_exit(PTHREAD_CANCELED)`（RT 信号在 OHOS 被静默吞掉）。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：**imv 5.0.1**（`src/imv.c:1242` `pthread_cancel(pipe_stdin_thread)` + 紧随的
  `pthread_join`）；同范式适用于所有 cancel→join 收线型软件。
- 机制来源：**配送池** `DRAFT-spiped-1.6.4-pthread-cancel-ohos-nonRT-signal-shim`
  （主理-8 2026-10-18 实撞写入池）。本条目是它**首次随真实 PR 交付**，读数由本任务
  （平台任务 7452 / 链主-97）独立复跑。

## 错误特征

- 编译期（`c_std=c99`）：
  `warning/error: call to undeclared function 'pthread_cancel'; ISO C99 and later do not
  support implicit function declarations`
- 链接期：`ld.lld: error: undefined symbol: pthread_cancel`
- 若绕过链接（`--unresolved-symbols=ignore-all` 或 `return 0` 空实现）：
  运行期**永久挂起**在 `pthread_join`（取消请求返回 0、线程根本没被解除阻塞）

## 根因（三层，逐层实测）

1. **头文件层**：SDK sysroot 的 `<pthread.h>` 完全不声明这 4 个函数——
   `grep -c pthread_cancel <sysroot>/usr/include/pthread.h` = **0**
   （`PTHREAD_CANCELED` 等宏常量仍在，第 82 行）⇒ 编译期只报警/报未声明。
2. **桩库层**：同一 sysroot 的 `libc.so` 不导出——
   `llvm-nm -D --defined-only <sysroot>/usr/lib/aarch64-linux-ohos/libc.so | grep -c pthread_cancel`
   = **0** ⇒ 链接期 undefined symbol。
3. **运行时层**：设备 `/system/lib64/libc.so` 有 `T pthread_cancel`，但调用即
   **rc=38 (ENOSYS)**（探针 `repro/pc_probe.c`：`dlsym(RTLD_DEFAULT,"pthread_cancel")`
   取到函数指针，`pthread_cancel(pthread_self())` → 38）⇒ 「取消阻塞线程」永不生效，
   join 永久阻塞。

**信号对照（本平台独有）**：`sigaction(SIGRTMIN)` 与 `pthread_kill(self,SIGRTMIN)`
都 rc=0，但 handler **got=0**（RT 信号被静默吞掉）；同一探针对 SIGUSR1 为 **got=1**。
⇒ 经验库 12d §4 记的「SIGRTMIN + pthread_exit」在本平台无效，须用非 RT 信号。

## 修复（零上游补丁，配方侧落地）

1. `generate()` 写出兼容 TU（4 个 API）与声明头：
   - `pthread_cancel(t)`：首次调用时对 **SIGUSR1** 装 handler（handler 内
     `pthread_exit(PTHREAD_CANCELED)`），随后 `pthread_kill(t, SIGUSR1)`；
   - `pthread_setcancelstate/type` 退化为记录型空实现、`pthread_testcancel` 为空。
2. `-include <compat.h>` 消掉 undeclared-function（c99 下是硬错误）；
3. 把编出的 `.o` 挂到链接行（meson：`tc.extra_cflags` / `tc.extra_ldflags`；
   autotools：CPPFLAGS/LDFLAGS；CMake：`target_link_libraries` / `CMAKE_C_FLAGS`）。
4. 前置检查：`grep` 确认上游未占用 SIGUSR1（imv 实测 `src/` 内无
   `SIGUSR1/sigaction/signal()` 调用，安全）。

imv 落点：`archives/i/imv/5.0.1/conanfile.py` 的 `_CANCEL_*` 常量 + `_build_cancel_compat()`。

## 验证（本任务实测）

```text
# 改前（链接 imv 目标）
ld.lld: error: undefined symbol: pthread_cancel

# 改后
52/52 目标全部链接成功；meson test（上游 3 目标）Ok: 3 / Fail: 0 ⇒ 5/5
消费者测试 passed=14 failed=0 skipped=0

# repro/cancel_join_test.c（取消阻塞在 read() 的线程再 join）
[test] pthread_cancel -> 0
[test] pthread_join   -> 0
[test] reader_returned=0
```

## 适用边界 / 反例

- **适用**：真依赖「取消 → 解除阻塞 → join 返回」的收线路径。
- **不适用 / 不必用**：只探测 pthread 可用性（走 E085 / `cc.has_function` 宏守卫）；
  只「尽力取消」且不 join（`return 0` 即可）；上游已占用 SIGUSR1 或依赖延迟取消语义
  只在取消点退出（须改用协作式唤醒或 detach）。
- **代价**：进程级占用一个非 RT 信号；语义是立即取消而非延迟取消。

## 查重与新增价值

**与正式条目 E513 的边界（判 create 的主依据，手册/03 §6.2 注 2）**

- **同**：症状签名（`undefined symbol: pthread_cancel` / `call to undeclared function`）与
  核心机制（非 RT 信号 + handler 内 `pthread_exit` + `pthread_kill` + `pthread_join`）一致；
  E513 的 `rec_approach=guarded-signal-thread-exit`、`rec_command` 即
  `pthread_kill(thread, SIGUSR1)` + `pthread_join`。
- **不同 1（交付形态）**：E513 `rec_impl: source-patch`——要改上游源码里创建可 join 线程 /
  设置取消点的位置；本条是**零上游补丁的配方侧注入**（配方生成兼容 TU + `-include` 强制声明 +
  把 `.o` 挂链接行，本包 `patches: {}` 实测通过），对「打包他人上游、不便改源码」的场景可直接复用。
- **不同 2（语义细节）**：本包 handler 用 `pthread_exit(PTHREAD_CANCELED)`（E513 用
  `pthread_exit(0)`），使 `pthread_join(&retval)` 能取到 PTHREAD_CANCELED。
- **不同 3（两条平台事实，E513 未载）**：① 运行时 `/system/lib64/libc.so` 导出
  `T pthread_cancel` 但调用返回 **ENOSYS(38)**（空壳 ⇒ `nm` 有导出不等于可用）；
  ② **RT 信号被静默吞掉**（`sigaction`/`pthread_kill` rc=0 而 handler got=0，SIGUSR1 got=1）
  ⇒ 推翻经验库 12d §4 记的「SIGRTMIN + pthread_exit」路线。
⇒ 按 §6.2 注 2「多一条可选路径 + 它的适用面与代价本身就是可复用知识」判 **create**。


- 同症状既有条目 **E085 / DRAFT-E680 / DRAFT-xmcd-3.3.2 / DRAFT-20003 /
  DRAFT-aml-1.0.0** 的解法分别是：探测+空实现、集中 shim 补符号、特性宏+跨线程取消降级为
  空操作、关硬取消走软取消+测试超时守卫、Meson 特性检测宏守卫。**五条全文都不含信号方案**，
  也都不解决「跨线程取消真的解除阻塞」。本条给出的「非 RT 信号 + handler 内 pthread_exit」
  及其平台事实（运行时导出但 ENOSYS；RT 信号被吞而 SIGUSR1 可用）未被覆盖
  ⇒ 按手册/03 §6.2 条件 2 判 **create**。
- 与配送池 `DRAFT-spiped-1.6.4-pthread-cancel-ohos-nonRT-signal-shim` 的关系：机制同源，
  该池件宿主包 PR 未交付、从未随 PR 走过 draft-review；本条是**首次交付批次**，
  并把「改前/改后」读数补齐到本包。
