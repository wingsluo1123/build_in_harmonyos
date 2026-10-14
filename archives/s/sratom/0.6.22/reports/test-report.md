# 测试报告 — sratom 0.6.22 (OHOS PC / aarch64-linux-ohos)

> 遵循 R51「上游测试三步法」：①清点 → ②实跑 → ③如实回填。

## 一、上游测试清点（Step 1）

上游 test/ 含 **2 个注册单元测试 + 1 个头文件探针套件**：

- `test/meson.build`：`unit_test_names = ['trip', 'write']`，meson `test()` 注册（suite: 'unit'），源 `test_trip.c` / `test_write.c`（共享 `forge_test_object.c` / `test_uri_map.c` 夹具）；
- `test/headers/`：`test_headers` 可执行（编译期警告探针，非断言型用例）。

清点数 = **2**（注册用例）+ 1 探针（单列）。

## 二、实际运行（Step 2）

交叉编译产物（OHOS aarch64 ELF，构建目录直出）逐用例实跑：

| 用例 | 命令形态 | 退出码 | 结果 |
|---|---|---|---|
| trip | `LD_LIBRARY_PATH=build:... ./test/test_trip` | **0** | 输出 `All tests passed.`（glib testing 框架全绿） |
| write | 同上 `./test/test_write` | **0** | 输出全部为上游**故意触发**的警告路径（ambiguous atom:Path / Unknown language URID），无 FAIL |
| headers（探针） | `./test/headers/test_headers` | **0** | 头文件包含性检查通过 |

**2/2 注册用例通过 + 探针通过，100% 实跑覆盖**（证据：`reports/` 下逐用例日志）。

## 三、PR 回填数据（Step 3）

| 指标 | 数值 |
|---|---|
| 上游测试清点 | 2（trip/write，suite=unit）+ 1 探针单列 |
| 上游测试实跑 | **2/2 通过（100%）**，逐用例退出码 0（trip 有 `All tests passed.` 断言输出；write 为上游设计的警告路径验证，rc=0） |
| 鸿蒙特有测试 | 1（消费者测试：sratom 序列化往返一致性，见 test_package/） |
| 补丁 | 0（探索期零源码修改，`diff -rq` 证实） |

## 四、结论

上游测试全部真实执行并通过；鸿蒙特有消费者测试承担 CI 回归职责。

## 五、鸿蒙特有消费者测试实测（2026-10-12）

```
INFO: Int turtle: <http://example.org/s>
	<http://example.org/p> "42"^^<http://www.w3.org/2001/XMLSchema#int> .
INFO: Object turtle: <http://example.org/s>
	<http://example.org/p> [
		a <http://example.org/Coord> ;
		<http://example.org/x> "2026"^^<http://www.w3.org/2001/XMLSchema#int> ;
		<http://example.org/label> "harmonyos-pc"
	] .
INFO: label round-trip: "harmonyos-pc"
INFO: x round-trip: Int 2026 (upstream xsd:int mapping)
PASS: sratom consumer test (forge -> turtle -> parse -> field-by-field round-trip)
```

- Int32 原子：Turtle 序列化含 xsd:int 类型注记，往返 body 字节级全等；
- Object 原子：属性数 2、label String 字段无损往返、x 属性经 sratom 的 xsd:int 映射回读为 atom:Int 值 2026（实测EA 07 00 00 字节证据）；
- 真实数据链路（forge→to_turtle→from_turtle→逐字段断言），非纯断言。
