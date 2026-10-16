# tsdecrypt 10.0 HarmonyOS PC 适配说明

## 构建

- 构建系统：上游 Makefile
- 目标：HarmonyOS PC armv8，Clang 15
- 依赖：`openssl/3.0.21`、`libdvbcsa/1.1.0`
- 状态：built（发布后由仓库流程更新）

配方从三个上游官方归档恢复主仓和两个固定提交的子模块，应用九个可审计补丁，使用外部 libdvbcsa 完成构建，并对最终 ELF 清除旧签名后执行一次签名。

## 上游测试清点（R51）

| 项目 | 数量 | 实际执行 |
|---|---:|---:|
| 顶层 `test/tests` 目录 | 0 | 0/0 |
| 顶层 `make check/test` 目标 | 0 | 0/0 |
| CTest 注册 | 0 | 0/0 |
| 随源码提供的独立 runner | 2 | 2/2 |

两个 runner 分别为 `FFdecsa/FFdecsa_test` 和 `libtsfuncs/tstest`。前者完成 10 组固定/样例正确性比较并继续执行随机与吞吐路径；后者完成 32 个生成器往返检查。报告口径按 runner 计为 2/2，不将内部循环膨胀为独立测试数。

## 适配修复

1. 为现代 C 编译器补齐 `stdlib.h` 与 `crypt.h` 声明。
2. 让依赖扫描继承外部依赖头文件路径，并使用标准定宽整数类型。
3. 由配方声明目标 libc 缺少 pthread cancellation 能力，源码通过能力宏选择同步 DNS
   解析路径，不在补丁中引入平台宏。
4. 修复 libtsfuncs runner 命中的自动对象生命周期错误和只读字符串写入。
5. RTP 输入不再固定剥离 12 字节：解析版本、payload type、CSRC、扩展和 padding，并在交给 TS 处理器前验证长度与每个 188 字节包的同步字节。
6. UDP 读取按单个完整数据报返回，避免扩大接收缓冲区后等待填满 65535 字节。

## 验证

- 上游 runner：2/2 通过。
- 安装后真实 CLI 消费者场景：17/17 通过。
- 覆盖基础 RTP、marker、CSRC、扩展、padding、组合头以及截断、错误 PT、越界长度、错误 TS 对齐等负例。
- 检查 AArch64 OHOS ELF、唯一 `.codesign`、无 RPATH/RUNPATH、无 Conan 缓存路径，并验证 libdvbcsa 动态闭包。

完整 QTV/CAMD 服务器互操作不属于本次 RTP 输入边界修复的触发条件，未计入通过数。

## 发现与知识

- ✅ 已提取：RTP 可变头部和尾部 padding 必须共同参与有效载荷边界计算，见 `knowledge/drafts/E429-draft-1BEB.md`。
- ✅ 已提取：MPEG-TS 对齐与同步字节验证必须基于完整 UDP 数据报，不能先固定截断再推断，见同一知识草稿。

---

**编译结束**: 2026-10-15 13:53
**最终状态**: built
