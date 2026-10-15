# minieigen 0.50.3 测试报告

## 结论

HarmonyOS/OHOS AArch64 Release 构建、打包、上游 runner、消费者 API 和
Python ABI 发现对照全部通过；最终制品又在 HarmonyOS PC 真机以随包目标
Python 完成动态加载与同 ELF 双后缀对照。

## 构建矩阵

- Conan reference：`minieigen/0.50.3`
- 配置：`os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15, build_type=Release`
- 目标 Python：`python/3.12.9`
- 扩展：`minieigen.cpython-312-aarch64-linux-ohos.so`
- 最终 ELF SHA256：`f59c1aaa673b317c4fe61de5a34bb4727de3fa4324c98b5be810bc37ef406f94`
- 最终 W3 日志 SHA256：`66f677902239353c5a8d92ed28149dd68bc4d99768f4c191123f2ba91db1d86b`
- 真机闭环日志 SHA256：`60903a25b90ba1b0b085fbf573a73b704e466ad23e750775324df6c0261c81a7`

## 上游测试

| 上游入口 | 清点 | 执行 | 结果 |
|---|---:|---:|---|
| `src/basic-test.py` | 1 | 1/1 | PASS |
| runner 内可观察计算与转换 | 31 | 31 项均执行 | 非逐项预期值断言 |
| `test/` / `tests/` | 0 | 0/0 | 上游无此目录 |
| CTest / `make check` | 0 | 0/0 | 上游无此入口 |
| vendored `src/double-conversion/*test*` | 0 | 0/0 | 无断言且 Makefile 只编译不执行；vendored 实现已由 `double-conversion/3.4.0` 替代 |

上游 runner 原为 Python 2 `print` 语法；补丁机械转换为 Python 3 语法，
并清理 7 个仅用于分隔的空白行，没有删减原有操作。

## 新增消费者与 HarmonyOS 专项验证

- 12 项目标 Python 显式断言：后缀、ELF 架构、向量、矩阵、逆矩阵、
  旋转、四元数和包围盒。
- 3 项扩展发现对照：本次实测构建端 Python 3.14 后缀必须被目标 Python
  拒绝；目标 `EXT_SUFFIX` 必须可导入；两臂扩展的 SHA256 必须相同。
- 静态硬门禁：AArch64 `e_machine=183`、`PyInit_minieigen`、预期
  `DT_NEEDED`、无绝对 `DT_NEEDED`、无 RPATH/RUNPATH、恰好一个 `.codesign`。

正式测试计数为上游 runner 1 项加新增显式断言 15 项，合计 16 项；不少于
上游实际的 1 个 runner。31 仅表示该 runner 内全部执行的可观察操作数，
不作为 31 个带预期值的测试用例或断言申报。

## 关键结果

```text
HMBS_UPSTREAM_TEST_RESULT: 1/1 runner passed; 31 upstream observable operations executed
PASS: 12 minieigen consumer assertions
PASS: foreign build-interpreter suffix rejected; target EXT_SUFFIX loaded
```

## HarmonyOS PC 真机闭环

- 随包 `python/3.12.9` 实测 `SOABI=cpython-312-aarch64-linux-ohos`、
  `EXT_SUFFIX=.cpython-312-aarch64-linux-ohos.so`。
- 真机完成上游 runner 1/1（31 项操作）、消费者断言 12/12。
- Arm B 使用 `.cpython-314-x86_64-linux-gnu.so` 返回 1，明确为
  `ModuleNotFoundError`；Arm C 使用目标后缀成功导入。
- 两臂 ELF SHA256 均为
  `f59c1aaa673b317c4fe61de5a34bb4727de3fa4324c98b5be810bc37ef406f94`。
- 真机加载闭包包含 `libboost_python312.so`、`libpython3.12.so.1.0`、
  `libdouble-conversion.so`、`libc++_shared.so` 与 `libc.so`；无
  RPATH/RUNPATH，且 `.codesign` 恰好 1 个。

上游数值输出包含随机生成的示例矩阵，因此不把全部 stdout 固化为黄金文件；
消费者测试使用确定性输入和数学不变量判定。
