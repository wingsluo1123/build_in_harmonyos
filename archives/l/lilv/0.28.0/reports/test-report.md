# 测试报告 — lilv 0.28.0 (OHOS PC / aarch64-linux-ohos)

> 遵循 R51「上游测试三步法」：①清点 → ②实跑 → ③如实回填。

## 一、上游测试清点（Step 1）

上游 test/ 含 **21 个注册单元测试**（test/meson.build `unit_tests` 数组，meson test() 注册，源 test_<unit>.c + lilv_test_utils.c 夹具，LILV_TEST_BUNDLE 指向构建目录内 test_plugin.lv2）：

bad_port_index, bad_port_symbol, classes, discovery, get_symbol, no_author, no_verify, plugin, port, preset, project, project_no_author, prototype, reload_bundle, replace_version, state, ui, util, value, verify, world

另有 headers/lint 探针目录（编译期检查，非断言用例，单列）。

清点数 = **21**（注册用例）。

## 二、实际运行（Step 2）

交叉编译产物（OHOS aarch64 ELF，[130/130] 零失败）逐用例实跑（LD_LIBRARY_PATH=build 目录 + conanrun 环境）：

```
PASS=21 FAIL=0
```

**21/21 全部通过（100% 实跑覆盖）**，逐用例日志见 $HOME/tmp/lilv-t-<unit>.log（test-plugin 的插件发现链路含 test_plugin.lv2 bundle 加载，真实 I/O）。

## 三、PR 回填数据（Step 3）

| 指标 | 数值 |
|---|---|
| 上游测试清点 | 21（meson unit_tests 数组全列） |
| 上游测试实跑 | **21/21 通过（100%）** |
| 鸿蒙特有测试 | 1（消费者测试：包内 liblilv-0 真实枚举插件，见 test_package/） |
| 补丁 | 0（探索期零源码修改） |

## 四、结论

上游测试全部真实执行并通过（21/21）；鸿蒙特有消费者测试承担 CI 回归职责。

## 五、鸿蒙特有消费者测试实测（2026-10-12）

```
INFO: discovered http://example.org/consumer-test-plugin
INFO: name = "Consumer Test Plugin"
INFO: ports = 3
INFO: port symbols = in/out/gain
PASS: lilv consumer test (bundle discovery -> parse -> introspection)
```

- LV2_PATH 发现 → liblilv-0 真实加载/解析 fixture bundle（Turtle 链路走包内 serd/sord/sratom）→ introspection 断言（doap:name、端口数 3、端口符号 in/out/gain）全部通过；
- 修复记录：port symbol API 为 get_port_by_index+port_get_symbol 两步取（0.28.0 无 plugin_get_symbol_by_index）；port_get_symbol 返回值由 port 持有不得 free（lilv.h 所有权文档，free 即 SIGSEGV——实测定位）。
