# LIVE555 2025.05.24 HarmonyOS PC 适配笔记

## 范围与依赖

- 目标：HarmonyOS PC / AArch64，Clang 15，Release。
- 源码：VideoLAN 权威发行镜像 `live.2025.05.24.tar.gz`，SHA256
  `e6185902c4bfe9235067a0bc80ec9a5f8a95956d9d07525ce169f3f9753afb0a`。
- 默认 OpenSSL 功能未关闭，固定依赖 `openssl/3.5.8.1`；TLS、SRTP、HMAC
  相关源码均参与构建。
- 交付四个静态库及公共头文件，不交付示例/服务器二进制，因此软件级类型保持
  library，不需要 `commands.json`。

## 上游资产清点

此版本没有注册的 `check`、`test` 或单元测试套件，上游自动测试基数为 0。
源码包含 34 个默认 `testProgs` 程序以及三个服务器程序，共 37 个自包含目标，
已全部在真机构建。另有 `extra` 下的 `testGSMStreamer` 骨架；发行包没有
`testGSMEncoder.cpp`，其源码注释要求用户自行提供 `createNewGSMAudioSource()`，
故该目标被清点为 1 个不适用的可选骨架，未伪造实现或计作测试。

这些程序多数依赖媒体文件、网络对端、长时间服务或人工交互。构建成功只记录为
程序目标构建成功，不冒充自动测试通过。适配后新增一个安装后 HarmonyOS PC
消费者场景，内部有八项行为断言，结果 8/8。

## B 类问题与修复

原始 `triggerEvent()` 只设置 atomic flag，无法唤醒阻塞在 `select()` 的事件
线程。默认构造以 10 ms 周期 tick 保证触发器最终被处理，空闲时也持续返回；
如果仅取消 tick，跨线程触发会等到其他 I/O、定时器或 watchdog。

正式补丁在 scheduler 的读取集合中注册非阻塞、`FD_CLOEXEC` 的 Unix datagram
socketpair。发布线程先写入 `clientData` 并将相应 bit 从 idle 变为 pending，
随后只对这次新置位的 bit 发送通知。事件线程将通知通道排空，继续使用原有轮转
逻辑处理一个 pending trigger；若仍有可枚举的 pending bit，退出 `SingleStep()`
前重新置为可读。由此即使通知在满队列上合并为 `EAGAIN`，也不会留下无通知的
pending bit。`EINTR` 重试；永久错误给出诊断。析构时先注销
读端再关闭两端，调用契约要求生产线程停止并 join 后再销毁 scheduler。

默认 granularity 改为 0；调用者明确传入正值时仍保留周期 tick。如果通道创建、
非阻塞/CLOEXEC 设置、`FD_SETSIZE` 检查或注册验证失败，则回退到 10 ms tick，
不牺牲事件活性。

## 验证结果

- W0：`openssl/3.5.8.1` 的完整 OHOS armv8 图以 `--build=never` 解析通过。
- 目标真机：HUAWEI MateBook Pro HAD-W32，HongMeng Kernel 1.12.0，aarch64。
- 三臂：原始臂失败；仅取消 tick 的错误修复臂失败；正式主动唤醒臂通过。完整
  命令、共同判定器、结果与哈希见 `reports/path-b-evidence.md`。
- 正式 `conan create`：37/37 适用程序目标构建完成；四库、182 个公共头文件与
  license 打包完成；安装后消费者 8/8 通过。
- 消费者实测：public 无参数 factory 在空闲 250 ms 内没有 10 ms 周期
  `select()`；显式零粒度 `SingleStep()` 返回 1 次；显式 10 ms 粒度
  返回 25 次；十次跨线程触发 P95 为 0.074 ms；组合 32 bit、四线程发布以及
  人工填满通知队列、确认发布命中 `EAGAIN` 后的 32 个 trigger 仍处理 32/32；将文件描述符上限临时约束
  为 3 后，初始化失败正确选择 10 ms tick 回退。

## 知识边界

E1078 讨论 musl/OHOS 缺少 pthread cancel 时如何协作退出线程；本项目不涉及
取消或退出，而是正常事件交付时“状态发布”与“阻塞等待通知”必须配对。两者可能
都使用 fd/有限等待机制，但问题、正确性条件和测试预言机不同。

“空闲低轮询”只指受控条件下没有业务 I/O 和其他 timer 时 scheduler 的
`SingleStep()` 返回次数，不宣称系统级零唤醒或直接量化节能。
---

**编译结束**: 2026-10-17 17:35
**最终状态**: built
