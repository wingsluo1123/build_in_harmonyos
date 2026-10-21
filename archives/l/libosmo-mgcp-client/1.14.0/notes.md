# libosmo-mgcp-client 1.14.0 HarmonyOS PC 适配笔记

## 结论

- `conan create` 返回 0。
- 消费者成功初始化 MGCP client，输出
  `LIBOSMO_MGCP_CLIENT_CONSUMER_OK`。
- 制品包含 `libosmo-mgcp-client.so.14.1.0`、符号链接、5 个公开头、
  1 个生成头和 pkg-config 文件。

## 来源与范围

该库来自 `osmo-mgw 1.14.0` 源包，本任务只打包 MGCP client 库，
不包含 Media Gateway 服务程序。

## 构建适配

- 直接编译 `src/libosmo-mgcp-client/*.c` 5 个文件。
- `MGCP_CLIENT_LIBVERSION=14:1:0` →
  `libosmo-mgcp-client.so.14.1.0`，SONAME `.so.14`。
- 生成 `mgcp_common.h` 并安装到公开 include 树。
- 与 libosmocore 统一使用原生 TLS 模型 `-fno-emulated-tls`。

## 上游测试

- `tests/mgcp_client/mgcp_client_test`
- `tests/mgcp/mgcp_test`

两个测试均实际运行通过，输出分别与上游 `.ok/.err` 文件逐字节一致。
测试驱动将对应上游库源文件直接编入可执行程序，未修改测试源码或
期望输出。
