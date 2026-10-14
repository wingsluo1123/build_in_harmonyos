# E595 — musl 以 NULL 定义 glibc 的 program_invocation_name 系列导致启动崩溃

## 错误特征

- 进程**无任何输出**直接退出，退出码 rc=139（SIGSEGV）。
- stdout / stderr 完全为空，没有任何日志行——这是最迷惑人的地方。
- 用 gdb 运行可在栈顶看到 `strdup` 内崩溃，参数为 `NULL`。
- 同一软件包内，**不链接 setproctitle.o 的另一个可执行文件运行正常**（关键判据）。

## 触发条件

- 构建系统: makefile / cmake / autotools（与构建系统无关）
- 阶段: runtime（启动早期，`main()` 内进入事件循环之前）
- 平台: musl libc 环境（含 OpenHarmony / HarmonyOS PC aarch64）
- 上游特征: 自带 `setproctitle.c`（spt_init）、或任何对 `program_invocation_name` /
  `program_invocation_short_name` 做 `strdup()` 深拷贝的启动代码

## 根因分析

glibc 在程序启动时由运行时填充两个全局量：

- `program_invocation_name` —— `argv[0]` 全路径
- `program_invocation_short_name` —— `basename(argv[0])`

musl **不提供**这两个符号。集成方为此写的兼容层/shim 往往只能把它们**静态定义为 NULL**。
上游若在启动早期对它们做深拷贝（`setproctitle` 的 `spt_init()` 就是典型），
`strdup(NULL)` 立刻解引用空指针 → 进程在打印任何输出之前崩溃。

因为崩溃发生在日志初始化之前，所以表现为"静默 SIGSEGV"，从日志完全看不出线索。

## 解决方案

### 推荐方案

在**启动最早阶段**（进入 `main()` 后、调用 `spt_init()` 之前）按 glibc 语义补齐取值，
让原有的深拷贝照常工作：

```c
/* 置于 main() 最前部，早于 spt_init()/任何 strdup(program_invocation_*) */
program_invocation_name = argv[0];
program_invocation_short_name = strrchr(argv[0], '/')
    ? strrchr(argv[0], '/') + 1 : argv[0];
```

（实际落地时按上游变量的链接类型决定是否 writable，必要时在兼容层提供
`extern` 可写定义以供赋值。）

### 禁止做法

- ❌ 把 `program_invocation_name` / `program_invocation_short_name` 定义成 `NULL`。
  这不是"占位"，而是把"取值"变成"必崩"，只是把崩溃推迟到第一次读取。
- ❌ 只在 `strdup` 处打补丁而不修全局量——其他读取点仍会崩。

## 验证

```bash
# 1) 看是否无输出即崩
./<prog> ; echo "rc=$?"        # rc=139 且无输出 → 命中本模式

# 2) 同包对照：不链接 setproctitle.o 的那个可执行文件应正常
./<prog-without-setproctitle> ; echo "rc=$?"

# 3) gdb 定位
gdb -batch -ex run -ex bt ./<prog>   # 栈顶应为 strdup(NULL)
```

修复后 `./<prog>` 应能正常启动并打印版本或监听日志。

## 关联条目

- 相关: E627（同为"平台能力缺失被上游当作必然可用"的启动期崩溃）
