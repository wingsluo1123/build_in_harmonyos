# CI #93279：构建并发与进程资源

CI-006的L0/KC/JC及CMake配置均通过。失败发生在Ninja启动编译任务时：

```text
cmake --build ... -- -j20
ninja: fatal: posix_spawn: Resource temporarily unavailable
```

没有出现编译器源码错误或未定义符号。缺失curl只影响预下载，Conan随后已成功下载并配置，
不属于本次失败点。旧CI #93178的worker-prep/git --version超时是另一轮基础环境问题。

## 修改

主配方和消费者的CMake.build均追加公开参数`build_tool_args=["-j1"]`。
Conan2.29.1先添加profile的jobs参数，再追加build_tool_args；实际命令为`-- -j20 -j1`。
原生Ninja实测确认最后的-j1将本包任务并发限制为1，匹配此前完整原生验证的构建并发。
没有更改共享profile、环境中的全局jobs或公共CI脚本。

## 已完成验证

- 原生Ninja执行6个计时任务，命令`ninja -j20 -j1`，全部完成；观察到的最大同时任务数=1。
- 原生Conan消费者以`-c tools.build:jobs=20`执行，CMake实际使用`-- -j20 -j1`。
- 29/29 Prolog + 1/1 C embedding =30/30、CONAN_TEST_RC=0；包括宿主栈三元组回归。
- 消费者日志SHA256：`1ff5021ab34716840e868d98cc5c9d9f5b1c8379d2506eb8383d203c3ca7090d`。
- 生产源代码、三个补丁、所选84个上游组及测试命令均未变。
  原84/84完整create证据仍是此前原生单任务构建记录；不冒充此次重新执行的结果。

此更改限制本包并发，不能保证在worker完全没有进程资源时仍能启动；新CI必须给出实际结果。
