# ladvd 1.1.2 路径 B 证据：测试宏内部函数名不是稳定接口

## 结论

本项目可形成一个边界明确的 B 类知识候选：迁移旧项目时，测试框架依赖升级
可能保持逻辑用例名不变，却改变宏生成的 C 函数名；凡是把该内部符号硬编码进
日志预期的测试都会产生假失败。修复应从当前 `__func__` 构造自反预期，同时
保留完整行为断言。

该主张不包含 Release `assert()` 副作用问题（正式知识 E259 已覆盖），也不把
HarmonyOS `/tmp`、`/var/run` 或 Unix socket 能力另行申报为新知识。

## 依赖演进证据

上游 `ladvd 1.1.2/configure.ac` 声明 `check >= 0.9.4`。三份 Check 官方
发布源码的 SHA256 与宏展开如下：

| Check | 官方源码 SHA256 | `START_TEST(test_my)` 生成的函数 |
|---|---|---|
| 0.12.0 | `464201098bee00e90f5c4bdfa94a5d3ead8d641f9025b560a27755a83b824234` | `test_my` |
| 0.13.0 | `c4336b31447acc7e3266854f73ec188cdb15554d0edd44739631da174a569909` | `test_my_fn` |
| 0.15.2 | `a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a` | `test_my_fn` |

官方 Git 标签分别解析为 `673dce1d61781c32b449bef0ee8711dc7e689170`、
`90d03f3fe002c33224432753ebfa21ebb5c32238` 和
`11970a7e112dfe243a2e68773f014687df2900e8`。Check 0.13.0 的发布说明也明确
记录 `START_TEST` 实现被重写。

## 同输入三臂

正式 ladvd 复现固定为 `START_TEST(test_my)` 内执行 `my_log(INFO, "debug")`
并完整比较标准错误文本；跨版本最小实验则用同一测试体从 `__func__` 生成等价
的 `actual` 文本，以便只隔离“框架实际函数名—期望构造”这一变量。

| 臂 | 期望构造 | 0.12.0 | 0.15.2 | 判定 |
|---|---|---|---|---|
| A 原始 | 固定 `test_my: debug` | 通过，退出 0 | 失败，实际为 `test_my_fn: debug`，退出 1 | 真机复现依赖升级故障 |
| B 假修复 | 固定 `test_my_fn: debug` | 失败，实际为 `test_my: debug`，退出 1 | 通过，退出 0 | 只是反向绑定另一版内部实现 |
| C 正确 | `snprintf(..., "%s: debug\\n", __func__)` | 通过，退出 0 | 通过，退出 0 | 跨两种宏实现保持原语义 |

最终补丁只改变期望值的来源，没有删除断言或降低比较强度。完整目标端验证仍以
`make check -j1` 的 7 个程序、45 个 `START_TEST` 用例为分母。

上述六个组合已在同一 HarmonyOS PC / aarch64 真机实际执行。0.12.0 与
0.15.2 均取自表中对应 SHA256 的官方发布源码，在任务私有隔离目录中构建；
两版使用完全相同的最小测试体、编译器和三种期望构造。由于旧版 Check 会优先
使用不可写的系统临时目录，实验构建仅覆盖其内部通信临时目录到可写缓存目录，
不修改 `START_TEST`、测试函数体或比较逻辑。0.12.0 仅用于验证向后兼容并排除
假修复，没有加入正式 Conan 依赖闭包。

三臂矩阵原始日志共 31 行、1,143 字节，SHA256 为
`f0a4c9aec0c655303e66f8db885ec90abe56bd22ba4f77f8b367a8815e0c7ac4`。
日志中的六个退出码依次为 `0,1,0,1,0,0`，且两个失败臂分别打印实际值
`test_my: debug` 与 `test_my_fn: debug`，因此不是只依赖预处理文本的推断。

最小实验的关键代码如下；`ORACLE_MODE` 分别取 0、1、2：

```c
snprintf(actual, sizeof(actual), "%s: debug\n", __func__);
#if ORACLE_MODE == 0
snprintf(expected, sizeof(expected), "test_my: debug\n");
#elif ORACLE_MODE == 1
snprintf(expected, sizeof(expected), "test_my_fn: debug\n");
#else
snprintf(expected, sizeof(expected), "%s: debug\n", __func__);
#endif
ck_assert_msg(strcmp(actual, expected) == 0,
              "actual=%s expected=%s", actual, expected);
```

复验时分别以两个官方版本的 `check.h` 和 `libcheck` 编译上述同一源码，然后
执行三个 `ORACLE_MODE` 产物；成功条件不是日志中出现某个名字，而是严格比较
返回 0。实验源、构建树和二进制均留在任务私有临时目录，不进入归档。

## 查重边界

- E259 覆盖 `NDEBUG` 删除 `assert()` 内副作用，与本问题无关。
- 现有 Check 草稿主要覆盖只读 `/tmp`、`TEMP` 优先级、测试注册或派发遗漏；
  未覆盖“依赖升级改变测试宏内部函数符号，导致自反日志预期失效”。
- 本项是测试链兼容知识，不宣称 ladvd 产品协议或网络能力出现 HarmonyOS 特有
  缺陷。最终是否认定为 B 仍由赛事复审决定。

## HarmonyOS PC 真机复验

设备为 HarmonyOS / HongMeng Kernel 1.12.0 / aarch64，运行相同的
`check/0.15.2` 依赖。直接运行 `check_util` 时显式设置 Automake 通常提供的
`srcdir`，避免把测试夹具路径缺失混入本机制：

- 原始臂：8 项中 7 项通过，唯一失败为
  `invalid output: test_my_fn: debug`，退出码 1；脱敏前原始日志 199 字节，
  SHA256 `67d7e021bf953116e6f5aae459c7ab01038ac4294b7b1a2074fd5a27decd08a7`。
- 正确臂：`check_util` 8/8，通过，退出码 0；日志 65 字节，SHA256
  `a7c6dfd849babdef6260a446001a319ab0abcd5fc587ef24402c2082b586352d`。
- 完整回归：最终十补丁构建执行 `make check -j1`，7/7 测试程序通过，退出码
  0；日志 2,857 字节，SHA256
  `e3e5aaf8e262a1dd502e12274a9a479385b9b31a72db094e2f8f2274619f70b1`。

原始日志保留在真机任务私有临时目录，不提交其中的个人 Conan 缓存绝对路径；
上述摘要和哈希用于绑定证据。正式 A 类迁移、全量回归与发布闭包始终使用制品
仓已发布的 `check/0.15.2`；自行构建的 0.12.0 只属于 B 类知识对照实验。
