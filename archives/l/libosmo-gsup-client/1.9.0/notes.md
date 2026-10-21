# libosmo-gsup-client 1.9.0 HarmonyOS PC 适配笔记

## 结论

- `conan create` 返回 0。
- 消费者执行 GSUP response 构造，输出
  `LIBOSMO_GSUP_CLIENT_CONSUMER_OK`。
- 制品包含 `libosmo-gsup-client.so.0.2.0`、符号链接、4 个公开头和
  pkg-config 文件。

## 来源与范围

该库来自 `osmo-hlr 1.9.0` 源包，本任务只打包 GSUP client 库，
不包含 HLR 服务程序和 mslookup 库。

## 构建适配

- 直接编译 `src/gsupclient/*.c` 中的 4 个库源文件。
- `LIBVERSION=2:0:2` → `libosmo-gsup-client.so.0.2.0`，SONAME `.so.0`。
- 显式链接 `libosmocore`、`libosmogsm`、`libosmoabis` 和 `talloc`；
  这些主体库并非都由组件 `cpp_info` 自动导出。
- 统一使用 `-fno-emulated-tls`。

## 上游测试

上游 9 个测试全部实际运行通过：

1. `auc`
2. `auc_ts_55_205_test_sets`
3. `gsup`
4. `db`
5. `db_upgrade`
6. `mdns`
7. `mslookup`
8. `mslookup_client`
9. `mslookup_client_mdns`

测试通过静态编入对应上游源文件、生成标准向量源码和临时 osmo-hlr
可执行文件完成；测试源码与 `.ok/.err` 期望未修改。
