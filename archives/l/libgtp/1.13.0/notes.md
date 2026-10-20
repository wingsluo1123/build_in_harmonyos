# libgtp 1.13.0 HarmonyOS PC 适配笔记

## 结论

- `conan create` 返回 0。
- 消费者测试通过：`LIBGTP_CONSUMER_OK`。
- 制品包含 `libgtp.so.11.0.0`、`.so.11`、`.so`、4 个
  `osmocom/gtp` 头和 4 个 legacy 兼容头。

## 来源与范围

`libgtp` 是 Debian `osmo-ggsn 1.13.0` 源包中的库组件；本任务只打包
`libgtp`，不包含 GGSN/SGSN emulator 可执行程序。

## 构建适配

- 直接编译 `gtp/*.c` 6 个文件。
- `LIBVERSION=11:0:0` → `libgtp.so.11.0.0`，SONAME `libgtp.so.11`。
- 生成最小 `config.h`，只启用库源码实际使用的 libc 头能力和版本宏。
- 链接 `libosmocore` 时统一使用 `-fno-emulated-tls`。

## 上游测试

上游共有 6 个测试：`ippool`、`ippool_v6`、`in46a`、`in46a_v6`、
`gtpie_test`、`queue_test`。

全部 6 个测试实际运行通过，输出与上游 `.ok/.err` 文件逐字节一致。
其中 `gtpie_test` 和 `queue_test` 在链接共享 `libgtp.so` 时会被
OHOS 动态加载器在 `main()` 前终止，因此测试驱动将同一份上游
`gtp/*.c` 源文件静态编入测试程序；未修改任何上游测试源码。

消费者测试直接调用公开 GTP IE API，覆盖相同的核心 TLV/TV 编码路径：

1. `gtpie_tlv` 成功；
2. TLV 长度正确；
3. type 字段正确；
4. value 数据正确；
5. `gtpie_tv4` 成功；
6. 32 位网络字节序正确。
