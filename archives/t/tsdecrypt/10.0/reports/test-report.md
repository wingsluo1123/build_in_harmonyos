# tsdecrypt 10.0 测试报告

## 环境与结论

- 目标环境：HarmonyOS PC aarch64，HongMeng Kernel 1.12.0，Clang/LLD 15。
- 配方：`tsdecrypt/10.0`，外部依赖为已发布的 `openssl/3.0.21` 与 `libdvbcsa/1.1.0`。
- 结论：上游 runner 2/2、安装后消费者场景 17/17、HarmonyOS 专项目标门禁
  2/2，均通过。

## 上游测试清点（R51）

| 上游入口 | 清点数 | 实际执行 | 结果 |
|---|---:|---:|---|
| 顶层 `test/tests` 目录 | 0 | 0/0 | 无入口 |
| 顶层 `make check/test` | 0 | 0/0 | 无入口 |
| CTest | 0 | 0/0 | 无入口 |
| `FFdecsa/FFdecsa_test` | 1 runner | 1/1 | 10 个 `CORRECT!`，通过 |
| `libtsfuncs/tstest` | 1 runner | 1/1 | 32 个 `generator is correct`，通过 |

计数以两个独立 runner 为 2/2，不把 runner 内部循环膨胀为独立用例。`FFdecsa_test`
还执行了随机与吞吐路径；`tstest` 在 `TZ=UTC` 下运行。两个 runner 均在真机上构建、
签名后执行。

## 安装后消费者验证

`test_package` 只调用 Conan 包中的最终 `bin/tsdecrypt`，通过真实 UDP 回环输入和文件输出
观察公共 CLI 行为。17 个场景如下：

- 合法输入 7 项：固定头、marker、两个 CSRC、零长度扩展、两字扩展、padding、
  CSRC+扩展+padding 组合。
- 非法输入 10 项：错误版本、错误 payload type、截断 CSRC、截断扩展头、扩展越界、
  零 padding、padding 越界、非 188 对齐、后续 TS sync 错误、超过单个 TS 帧上限。

每项同时验证输出字节序列与进程退出状态。冲刷帧使用与待测帧不同的内容标记，预言机
逐字节验证所有已输出数据；不把 UDP 接收缓冲或解密线程退出时保留的尾批次误判为协议
解析失败。

## HarmonyOS 制品门禁

以下两项不与上述 17 个 RTP 黑盒场景重复计数：

1. 制品静态门禁：最终程序为 AArch64 OHOS ELF，`.codesign` 恰好一节，不含
   `RPATH`/`RUNPATH` 或 Conan 缓存路径，且动态闭包包含申报的 `libdvbcsa.so`；
   OpenSSL 按最终链接结果闭合。
2. 目标端版本门禁：安装后的 `tsdecrypt --version` 在真机返回 0，且测试自动断言
   输出包含 `tsdecrypt v10.0`。

`MANIFEST.yml` 的 `assertion_count: 21` 按 17 个协议场景判定、3 个独立 ELF 门禁和
1 个精确版本输出断言统计；上游两个 runner 另行按 2/2 报告。

## 原始证据完整性

原始日志保存在仓外审计目录，未提交个人路径或构建缓存。对应 SHA256：

| 证据 | SHA256 |
|---|---|
| 真机完整 `conan create` | `44a9d9d5dfd78f0f04fe92d40dde6c86b40a4fbc50e717d23273c70fea9f74b7` |
| FFdecsa runner | `cbd3f4ffb3a1653ec977507a4e4e90808bef53519f3ef4b275c51eb2b1891cd3` |
| libtsfuncs runner | `385efc8ce3791dbb3e49727c70212dbb37ba2a9e7850cb13d2e10dcddd836242` |

以上三项哈希只绑定本次真机验证；正式 W3 证据单独列示如下。

正式 `finish` 已生成 `exit_code=0` 的 W3 回执。W3 的交叉构建阶段完成包结构、签名节、
动态闭包与可迁移性静态检查；交叉构建机不能执行 AArch64 OHOS ELF，因此不会把该阶段
计为 17 项运行通过。安装后公共 CLI 的 17/17 运行结论只来自上述真机 `conan create`。
本地 CI 完整日志 SHA256 为
`45bcd58794cea78fcd45d50350bfbfd86cb59ddb1a046177a8b72c7a5fa81377`。原始日志继续
保存在仓外，不作为提交内容。

## 边界

完整 CAMD 服务端互操作、真实加扰节目和长时吞吐不属于本次 RTP 负载边界修复的触发
条件，未执行且未计入通过数。
