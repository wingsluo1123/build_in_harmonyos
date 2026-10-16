# mailfront 2.12 适配笔记

## 当前阶段

已完成源码、语言、唯一性与依赖制品准入检查。官方源码在 HarmonyOS PC aarch64 上完成干净 Conan 构建、完整上游测试、消费者测试和路径 B 三臂实验，状态按规范保持 `built`。

## 构建配置

- 构建系统：上游自定义 Makefile
- 编译器：HarmonyOS clang 15
- 构建目标：`make -j1 all lua`
- 交付内容：10 个程序、19 个动态模块、3 个公共头文件

配方根据 Conan 依赖生成 `conf-cc`、`conf-ccso` 和 `conf-ld`，使用制品仓依赖编译；安装后对每个 ELF 去除调试信息、原位签名，并验证恰有一个 `.codesign`、没有 `RPATH/RUNPATH` 和 Conan 构建路径。

## 依赖版本

- `bglibs/2.04`
- `cvm/0.97`
- `lua/5.1.5`
- 测试工具：`cdb/20251021`、`openssl/3.5.8.1`

上述直接依赖均已在赛事制品仓发布并存在 OHOS armv8 二进制，不依赖未合入任务分支。

## 已解决的问题

1. 上游插件分别静态链接非 PIC 的 bglibs，在 HarmonyOS 共享模块链接时失败。主程序改为 whole-archive 提供并导出 bglibs 符号，插件仅保留自身 CVM/Lua 依赖。
2. 内部 `accept` 回调与 POSIX socket `accept()` 声明冲突，改为语义明确的内部名称。
3. 上游把模块目录作为编译期绝对路径写入主程序。适配后从 `/proc/self/exe` 解析同包 `../lib/mailfront`，保证 Conan 包可迁移。
4. HarmonyOS 应用数据文件系统拒绝队列后端使用硬链接发布临时文件；普通 `rename()` 会在并发命名碰撞时覆盖已有邮件，因此统一采用目标 libc 提供的 `renameat2(RENAME_NOREPLACE)`，不引入平台条件宏，同时保留原 `link()` 的“不覆盖”语义和原子发布性质。
5. UCSPI STARTTLS 在当前 mailfront 进程中替换输入输出描述符，但上游只设置 `tls_state`，保留了握手前的 SMTP 事务、EHLO 身份、认证副本和 relay 授权。新增独立安全边界 reset，在 TLS 切换成功与读取下一条命令之间完成撤销；普通 `handle_reset()` 仍保持“邮件事务重置”语义，发送第二封邮件不会注销。
6. 上游测试依赖宿主 PATH、硬链接、固定 `/tmp`、Linux 身份命令和实时 DNSBL 文本。测试补丁只做 HarmonyOS 沙箱与外部服务输出的等价适配，不减少或绕过任何上游测试实例。
   Spamhaus 实时查询在不同 Worker 可合法返回“已列入”或“未列入”；回归只接受这两个完整的标准输出之一，其他任何部分或异常输出仍失败，且测试数仍为 128。
   最终 W3 的真实 Spamhaus 查询覆盖“已列入”结果；另将同一生产测试指向不可解析测试域，强制验证两个“未列入”实例均通过，聚焦日志 SHA256 为 `d2834a5db5e687bdbc971d9e77af7be1da96ff535c255afd0f14b5d850a08919`。

## 上游测试清点（R51）

对官方 `mailfront-2.12` 的 `tests.sh` 和所有 `run_compare_test` 调用静态展开，并在最终真机构建中实际执行：

| 清点项 | 数量 | 实际结果 |
|---|---:|---:|
| 命名测试组 | 73 | 73/73 运行 |
| `run_compare_test` 展开实例 | 128 | 128/128 通过 |
| 失败 | 0 | 0 |
| 跳过 | 0 | 0 |

实际命令为 `sh tests.sh -v`。最终输出为 `128 tests executed, 0 failures`，没有以交叉编译或环境不足为由跳过上游用例。

## 新增目标端测试

正式 `test_package` 运行安装后的 `mailfront`、协议/后端/插件动态模块以及签名后的 CVM 测试模块，完成 7 个端到端场景、87 项外部可观察断言：

- 邮件事务状态在 STARTTLS 后撤销；
- 认证副本在 STARTTLS 后撤销，可重新认证；
- relay 授权在 STARTTLS 后撤销；
- EHLO 域名和 ESMTP 协议身份不跨越 STARTTLS；
- 普通邮件事务 reset 仍保留认证和 relay 权限；
- STARTTLS 前流水线注入的明文命令在升级后被拒绝，新 TLS 会话仍可继续。
- 真实 queuedir 后端在发布目标竞争时返回错误，仅清理自身临时文件，不删除或覆盖竞争者的已发布文件。

其中 HarmonyOS 目标端专项验证包括：签名 AArch64 ELF 及动态模块实际加载、UCSPI 描述符原地 TLS 切换、升级前后同一进程身份、以及可迁移模块发现与无 RPATH 闭包。

消费者还直接验证目标 libc 与应用数据文件系统上的 `renameat2(RENAME_NOREPLACE)`：目标已存在时必须返回 `EEXIST` 且旧内容不变，目标不存在时必须原子发布新内容。生产 `queuedir` 场景进一步确认碰撞后不会经 `queuedir_reset()` 删除竞争者目标。这两层检查共同防止队列适配退化为可覆盖或删除已有邮件的普通 `rename()` 路径。

## 路径 B 实证

同一真机、源码、工具链、依赖、桥接器和 6 场景探针仅改变安全 reset 实现：

- Arm A 上游原样：握手前事务、认证、授权、EHLO 和协议身份均残留；74 项脆弱行为断言通过。
- Arm B 伪修复：STARTTLS 后仅调用普通 `handle_reset()`，后端/插件 reset 已执行，但 SMTP 局部事务标志、认证、relay 授权、EHLO 和协议身份仍残留；74 项脆弱行为断言通过。
- Arm C 正确修复：独立安全边界 reset 撤销全部握手前语义状态；6 场景、76 项断言通过。

将 Arm A 或 Arm B 按“正确行为”运行时均稳定失败，首个失败点是 STARTTLS 后 `DATA` 未返回 `503`。详见 `reports/path-b-evidence.md`。

---

**编译结束**：2026-10-15
**最终状态**：built
