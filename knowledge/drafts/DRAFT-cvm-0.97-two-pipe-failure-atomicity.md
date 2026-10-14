# DRAFT — 多阶段 IPC 资源获取必须在 `fork()` 前形成失败原子提交点

## 触发实例

CVM 0.97 的 command transport 需要两组 pipe：一组把请求写给认证模块，另一组读取模块响应。上游实现为：

```c
if (pipe(pipe1) == -1 || pipe(pipe2) == -2) return 0;
pid = fork();
```

POSIX `pipe()` 失败返回 `-1`，所以第二次获取失败永远不会命中 `-2`。代码会带着未初始化的 `pipe2` 继续进入 `fork()`，错误路径可能误关任意描述符、错误布线子进程标准流或泄漏第一组 pipe。

## 可复用诊断

这不是普通的“检查返回值”问题，而是多资源事务缺少提交边界：只有全部资源获取成功后，才允许进入有外部副作用的 `fork/exec` 阶段；任一中间步骤失败时，必须按逆序释放此前已获取资源。

真实 `RLIMIT_NOFILE` 黑盒测试能证明修复后的返回值，但回退代码会读取未初始化描述符，外部现象受栈布局影响，可能同样返回 I/O 错误而假绿。因此验证必须直接约束控制流：对该编译单元替换 `pipe`、`fork` 和 `close`，分别注入第一次 pipe 失败、第二次 pipe 失败和 fork 失败，再验证正常父进程所有权转移；每个场景均断言调用次数、关闭顺序以及交付给调用者的 fd。

## 修复与验证闭环

1. 分开检查两次 `pipe()`；
2. 第二次失败时关闭第一组两个描述符；
3. `fork()` 失败时关闭两组四个描述符；
4. 保留真机 `RLIMIT_NOFILE=5` 黑盒测试，验证安装后共享库返回 `CVME_IO` 且没有执行模块；
5. 增加确定性编译单元故障注入，验证失败发生在副作用边界之前。

HarmonyOS PC / AArch64 实证：修复版四场景矩阵输出 `four-stage pipe/fork acquisition matrix is failure-atomic`；仅恢复上游 `-2` 判断后，同一测试稳定退出 2，并输出 `second pipe failure crossed the fork side-effect barrier`。完整包同时通过全部 52 个上游命名测试（76 次比较）和包消费者测试。

## 可执行最小验证

在已应用本配方补丁的 CVM 0.97 源码根目录执行：

```sh
cc -I. -I"$BGLIBS_INCLUDE" tests/pipe_failure_atomic.c \
  -o test-pipe-failure-atomic
./test-pipe-failure-atomic
```

预期退出码为 0，并输出 `four-stage pipe/fork acquisition matrix is failure-atomic`。该一个可执行文件内部依次运行第一次 pipe 失败、第二次 pipe 失败、fork 失败和父进程成功四个场景；任一场景的调用数、close 顺序或 fd 所有权不符即非零退出。

在临时源码副本中把 `client_xfer_command.c` 的第二次判断恢复为 `pipe(pipe2) == -2`，重新编译并执行同一命令，预期退出码为 2，并输出 `second pipe failure crossed the fork side-effect barrier`。安装后黑盒层由 `test_package/cvm_pipe_failure cvm_marker_helper MARKER` 在独立进程内将 `RLIMIT_NOFILE` 设为 5；预期共享库返回 `CVME_IO`、退出码为 0，且 `MARKER` 不存在。

## 跨项目佐证与边界

- Git v2.56.0（commit `a018953688f1b10bddf91bff8747068f5f4746a4`）的 [`start_command()`](https://github.com/git/git/blob/a018953688f1b10bddf91bff8747068f5f4746a4/run-command.c#L677-L735) 是同一模式的正面案例：它分阶段创建 stdin/stdout/stderr pipe，后续 pipe 创建失败时关闭已取得的描述符对，保存 `errno`，并在进入 `fork()` 之前返回。这证明“分阶段获取＋副作用前回滚”不限于 CVM 或认证协议。
- OpenSSH portable V_10_6_P1（commit `a8c72b842423f0774f542d3c2197247c3dd28d74`）的 [`ssh_proxy_connect()`](https://github.com/openssh/openssh-portable/blob/a8c72b842423f0774f542d3c2197247c3dd28d74/sshconnect.c#L220-L246) 连续创建两组 pipe，但任一创建失败就调用 `fatal()` 终止进程。这是适用边界：若 API 合同就是立即终止整个进程，资源可由进程退出回收；CVM 的函数返回错误并让调用者继续运行，所以必须局部、确定地回滚。不应把 `fatal()` 型代码机械改写为本条模式，也不应把它当作局部回滚的正面证据。

## 适用范围

适用于 pipe/socketpair/eventfd/open 等需要分阶段取得多个句柄、随后再启动线程、进程或注册回调的 C/C++ 代码。核心判据是“后续阶段具有不可轻易回滚的外部副作用”，而不是限定于 CVM 或认证协议。

## 查重边界

- `DRAFT-7324-BGLIBS-DJB-TWO-STAGE-CROSS-BUILD` 解决 SPAC 包装器的 build/target 工具链隔离；本条不申报该已知构建模式。
- E368 讨论 Meson/GNU ld `--wrap` 的 allocator/OOM 测试链接边界；本条关注多个 OS 资源的事务式获取顺序和副作用屏障，测试通过编译单元级符号替换，不改变被测共享库的链接模型。
- E244 讨论关闭句柄前保存错误值，E055 讨论 Python `posix_spawn`/errpipe 行为；二者都不覆盖“第二项资源失败后禁止进入 fork”的提交点。
- E261 是文件安装已提交后的身份绑定回滚，E394 是 `LD_PRELOAD` 初始化前准备 fixture；本条是进入副作用阶段之前的多句柄获取回滚，不涉及文件交换或动态加载器初始化时序。
- E386 覆盖 OHOS 存储目录的 `getcwd()` 诊断，本任务只复用其规避思路，不作为新增知识。

## 禁止做法

- 只断言最终错误码，不证明失败后没有进入 fork/线程/回调等副作用阶段；
- 依赖未初始化描述符恰好为某个值来制造回退失败；
- 第二次资源失败时只返回，不释放第一阶段已取得的资源；
- 为了测试而把生产共享库强制改成静态链接，扩大符号替换边界。
