# DRAFT-14488-3-musl-no-dt-init-no-argv-envp

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-14488-3-musl-no-dt-init-no-argv-envp.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-14488-3: OHOS 的 musl **不调用 `DT_INIT`、不向初始化入口传递 `argc/argv/envp`** —— 静态初始化器类库的适配诊断模式

- 条目主题：把「依赖 `DT_INIT`（`_init` 符号）完成接管」或「在初始化器中读取 `argc/argv/envp`」的库移植到 OHOS 时，会出现**静默 no-op**（初始化器从不执行）与**野指针崩溃**（拿到寄存器残留值当 `envp` 用）。含微观探针与两种规避方案。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：`archives/d/dynamorio/11.91.20676`（PR !14488）

## 适用场景

- 库「装上了但不生效」：例如注入/接管框架的行为与文档不符，且**无任何日志**（因为日志系统本身就在初始化器里启动）。
- 或进程在库初始化**极早期** SIGSEGV：崩溃点落在「遍历环境变量 / 读取辅助向量（auxv）」处。
- 上下游已知同族问题：DynamoRIO 上游对旧 Android 的 i#1862（loader 不给 lib init 传参）、对 musl 的 i#1973（musl 构造器不传参）注释均指向同一族语义。

## 诊断步骤（微观探针，无需 gdb）

```c
/* 1) DT_INIT 是否被调用：自定义 _init（注意 crti.o 也会提供 _init → 可能与链接冲突） */
/* 2) .init_array 是否被调用：__attribute__((constructor)) 或显式 .init_array 条目 */
/* 3) 初始化入口收到的参数是否为真：打印 argc/argv==NULL?  以及 envp 与 libc environ 是否同一指针 */
```
实测结论（OHOS PC aarch64）：
- `.init_array` 构造器 **会被调用** ✅
- `DT_INIT`（`_init` 符号）**不会被调用** ❌（因此只在 `_init` 里做初始化的库永不启动）
- 传给 `_init` 的 `argc/argv/envp` 为**寄存器残留值**（非 NULL、非真实环境；`envp != environ`）→ 直接遍历即 SIGSEGV

## 规避

1. **把初始化器挂到 `.init_array`**：对定义了 `_init` 的库，为其加 `__attribute__((constructor))`（等价于显式写 `.init_array` 条目）。上游已有先例：DynamoRIO 为 macOS ARM64（i#5383）采用同一 workaround。
   注意：若目标平台**同时也调用 DT_INIT**，会造成二次初始化 → 初始化体需**幂等**（静态标志）。
2. **不要信任初始化入口传入的 `envp`**：从内核侧获取环境更稳：
   - 用原始 syscall 读 `/proc/self/environ`（NUL 分隔）构造快照；同时**禁止**对该快照做 auxv 扫描（它不是栈布局，其后没有辅助向量）。
   - 不能图省事直接用 libc 的 `environ`：若该库以 `-nostdlib` 链接（自实现 loader 的框架常见），会留下未定义符号并被产物自检拒绝。
   - 页大小等 auxv 信息可退回**实测探测**（试映射 4096 后折半/加倍），避免依赖 auxv。

## 证据（本库实测）

- 在 DR 的 `our_init` 加最小 `write(2,...)` trace 后：`_init`/`our_init` 均被调用（`.init_array` 路径），但 `dynamorio_app_init` 之前即崩在 `os_page_size_init`（遍历野 `envp` 找 auxv）。
- 改为 `/proc/self/environ` 快照 + 禁用 auxv 扫描后：静态形态用例 `api.static_startstop` **rc=0**，输出 `in dr_client_main` 与 `Saw some bb events`（BB 事件真实触发）。
- 旁证：`libdynamorio.so` 若改用 libc `environ`，其产物自检直接报 `has undefined symbol: GLOBAL DEFAULT UND environ`（因 `-nostdlib`）。
