# lxi-tools 2.8 测试报告

## 结论

`lxi-tools/2.8` 在 HarmonyOS PC AArch64 原生环境完成构建、安装、签名和运行验证。上游登记 3 项条件元数据测试，当前环境实际注册并执行 2 项且全部通过；安装制品消费者的 14 个端到端场景、31 项外部可观察断言全部通过。

## 环境与制品

- 系统：HarmonyOS PC，AArch64。
- 编译器：clang 15，目标 `aarch64-linux-ohos`。
- Conan 包：`lxi-tools/2.8`，Release。
- 默认功能：CLI 与 GTK4 GUI 均启用并完成打包；目标端实际执行 `lxi-gui --help`，验证 GUI 可执行文件及其动态装载闭包。SSH 会话不具备图形 display，因此不把窗口呈现虚报为已验证。
- `lxi` 动态依赖摘要：`libxml2.so.16`、`libc.so`；无 `RPATH/RUNPATH`。
- `lxi` 与 `lxi-gui` 均恰有一个 `.codesign` 段。

## 上游测试

上游 Meson 按验证器是否存在条件注册三个元数据测试。配方使用已发布的 OHOS `desktop-file-utils/0.28` 提供 desktop 验证器，当前 OHOS 构建环境实际注册并运行 desktop 与 GLib schema 两项，结果为：

```text
Validate desktop file  OK
Validate schema file   OK
2/2 tests passed
```

上游测试总分母保持为 3。余下的 `Validate appstream file` 要求 `appstream-util`；该程序来自 `appstream-glib`，制品仓当前没有对应配方或 OHOS armv8 制品，因而未注册、未执行且不计为通过。仓中 `appstream/1.2.0` 提供的是接口不同的 `appstreamcli`，不能冒充上游指定程序。上游没有通用单元测试目录或另一套测试运行器。因此上游覆盖率为 2/3（66.7%），已执行部分通过率为 2/2（100%）。

## 新增消费者验证

正式 `test_package` 使用安装后的 `lxi` 与 `lxi-gui`，共 14 个场景、31 项外部断言：

1. 两个默认交付程序均存在。
2. `lxi --version` 返回 2.8。
3. `lxi-gui --help` 在目标端完成动态装载并正常退出。
4. 两个 ELF 均为 AArch64。
5. 两个 ELF 均恰有一个 `.codesign`。
6. 两个 ELF 均无 `RPATH/RUNPATH` 和 Conan 构建路径。
7. 目标端 `const.ohos.fullname` 非空。
8. 拆分发送的文本响应在换行到达后完整返回。
9. 分别拆分 `#`、位数字段、长度字段和 payload 的 definite-length block 完整返回，且 NUL 字节不丢失。
10. 完整帧到达后服务器继续保持连接，客户端仍在 1 秒内完成。
11. 非数字 definite-length 头和长度字段分别以非零退出。
12. `#0` 和声明超限分别以非零退出。
13. payload 提前 EOF 以非零退出。
14. 无终止符文本在统一总截止时间内以非零退出。

目标端最终输出：

```text
lxi-tools consumer scenarios: 14/14 PASS
```

其中 4 类属于 HarmonyOS 目标端专项检查：AArch64/签名 ELF、系统身份、真实目标动态装载闭包，以及安装后签名程序执行。其余协议场景同样在 HarmonyOS 真机执行，但不虚称为平台专有语义。

## 路径 B 回归

公共 `lxi scpi --raw` 与私有 loopback 假仪器完成三臂：

| 臂 | 返回码 | 耗时 | 标准输出 | 结果 |
|---|---:|---:|---|---|
| A 上游一次读取 | 0 | 268 ms | `ACME,` | 假成功、响应被截断 |
| B 等待连接关闭 | 1 | 1696 ms | 空 | 持久连接上超时 |
| C 协议边界组帧 | 0 | 655 ms | `ACME,MODEL\n` | 完整且在关闭前返回 |

详细共同条件、重现命令与证据哈希见 `path-b-evidence.md`。

## 原始证据保管

最终 W3 构建日志和目标端消费者复验日志含缓存路径，不进入 PR；它们保存在仓外审计目录，SHA256 为：

```text
27f9c46bccf7f831e6e1d0bb7abc7fcb252cbdb14e41d80f72d6a083984750f2  lxi-tools-2.8-w3-local-ci-r3.log
fe51ba1207e91914e28ec0fd78028b6cde151bcae3a9778ef6f8fdf913d9791a  lxi-tools-2.8-consumer-r2.log
```

这些哈希只绑定最终 14/14 运行；可复现依据是官方源码、提交的配方/补丁和 `test_package`，不要求签名 ELF 字节级重现。
