# uMurmur 0.3.1 测试报告

> 测试日期：2026-10-12
> 目标环境：HarmonyOS PC aarch64，HongMeng Kernel 1.12.0
> 构建环境：clang 15，Conan 2.29.1，OHOS 6.0 profile

## 测试摘要

| 类别 | 总数 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| 上游自动化测试 | 0 | 0 | 0 | 0 |
| 适配端到端场景 | 12 | 12 | 0 | 0 |

上游 `v0.3.1` 没有测试目录、CTest 注册、`make check` 目标或测试运行器，因此上游实测分母为 0。适配层运行 12 个端到端场景，共执行 31 项外部可观察断言，严格不少于上游；其中 4 类为 HarmonyOS 目标端专项验证。脚本中共有 41 个 Python `assert` 节点；其中 10 个是 Protobuf/OCB 辅助函数的内部不变量，不重复计入对外断言。

## 结果

- 官方 `conan-verify`：命令退出码为 0；G0、G1、G2、G3 实际执行并通过。生成器将 G4 标为 PASS 但注明未定位 package ID，L2/L4/L5 因同一定位问题跳过；这些产物检查由消费者与真机证据补足，不把“跳过”表述为“已执行”。
- 最终安装的 `sbin/umurmurd`：AArch64 OHOS ELF，恰有一个 `.codesign` 段，可在真机直接执行。
- 可迁移性：动态段没有 `RPATH/RUNPATH`；ELF 不含 `.conan2`、本项目构建目录或 package folder；从无关工作目录不带 `-c` 仍能解析并读取包内配置。
- 配置：合法配置接受；损坏的 libconfig 输入被拒绝。
- TLS：真实握手成功；客户端未发送任何应用数据前收到服务端 `Version` 帧。
- Protobuf-C：最小合法 Authenticate 被接受；收到 CryptSetup 与 ServerSync。
- 会话 UDP：使用 CryptSetup 返回的 key、client nonce 和 server nonce 完成 OCB 认证加密 ping 及解密回包。
- 公共 UDP：同一端口的状态查询返回并保留 token，用户数、容量和带宽字段有效。
- 负例：裸非 TLS 数据和超长协议帧均被拒绝，之后新 TLS 会话仍可建立。
- 生命周期：前台 SIGTERM 正常退出；守护模式创建 PID 文件，SIGTERM 后 PID 文件清理。

真机最终输出：

```text
uMurmur target closure passed: config + server-first TLS Version + protobuf auth + session-bound encrypted UDP + UDP status + malformed inputs + foreground/background SIGTERM
```

## HarmonyOS 目标端专项验证

1. 最终安装 ELF 必须包含且仅包含一个 `.codesign` 段，并能被 HarmonyOS 内核执行。
2. 在目标可写目录使用非特权端口运行前台和守护模式，验证 `fork/setsid`、PID 文件与 SIGTERM 清理。
3. 在目标网络栈上关联验证同一会话的 TLS 控制通道和 OCB 加密 UDP 数据通道，而非仅做无状态 UDP 探活。
4. 最终 ELF 不得带构建机 `RPATH/RUNPATH` 或本项目 Conan 路径；把包放到无关工作目录后，不带 `-c` 的配置校验仍须成功。

## 路径 B 对照

同一真机使用仓库内复现脚本完成三臂实验：上游臂握手成功但 Version 超时；队列直接触发 `POLLOUT` 的错误修复臂仍超时且 1 秒消耗 105 CPU ticks；TLS-ready 转换点排队修复臂收到 Version，空闲连接测量为 0 tick。详细命令、反例补丁和 CPU 计算方式见 `reports/path-b-evidence.md` 与 `reports/repro/`。

## 证据哈希

```text
正式消费者脚本  616901b997327e4c624f226cf54e48bb942cea018a22bee23bbf74c691f3ed8a
正确修复补丁    8f1ee51c78df4c70db53846967d51e84fb33f87111c9a28655509baa8ce2935b
最终真机 ELF    1eaa9a201fcae673b44b42c6537c57cd11b650a16af5e4427d7e159e2e9fd188
消费者输出日志  fc53ecef0b1e646296f20033da54e35a425fa61e6bd21eb34839be38acf22747
三臂构建脚本    c2623ed37074a211690621c843939a9caac5b6b73bd0800494599088b1538854
三臂探针        4fa896e80775444b593ad8b1622139a11bb8daf627d01b77ea3fe038c9fac5eb
Arm B 反例补丁  eacb7e638dd2590c421a576944ac5c895213c4c4fd3f283e0d37988b8c16920f
三臂输出日志    d933eb83037d866ce9fe6c29d91bb6d1e076c3b5a0607d5d561be686ca6755d0
```

实验 ELF 和含临时路径的完整构建日志不提交；仓库保留精确反例补丁、构建脚本、目标端探针、脱敏标准输出、测试边界和失败/修复对照，审核者可从官方源码与正式配方重建三臂。
