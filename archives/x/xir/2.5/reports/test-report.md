# xir 2.5 测试报告（HarmonyOS PC / aarch64）

> 日志留存说明：完整原始日志 `reports/conan-create.log` 与 `reports/upstream-test.log`
> 本地留存（gitignored，未随 PR 提交）；conan 缓存构建目录
> `~/.conan2/p/b/xir68676acccaf12/`（本地复现路径）。
>
> 检视修复轮（2026-10-17）：按 AI 检视意见修复 conandata/manifest 源码 URL
> http→https、test_package/test.cpp const 数据缓冲区补乘 4、gen_xmodel.cpp
> bias 独立 const op 后，清缓存完整重跑 conan-verify：G0-G4 全绿，上游测试
> 9 pass / 0 fail / 2 skip 与消费者 round-trip 结果不变，本报告行号引用与
> 新日志（710 行）对齐。

## 一、上游测试（R51 三步法）

### 1. 清点

| 项 | 结论 |
|---|---|
| `test/` 目录 | 存在，11 个自包含 main 程序（test/CMakeLists.txt 逐个 add_executable 生成 `<name>.bin`） |
| ctest / add_test 注册 | 无（`aux_source_directory` + add_executable，直接执行 .bin） |
| 自动化测试用例数 | **11** |

### 2. 可运行性

11 个 .bin 均为自动化断言（UNILOG FATAL abort 即失败）。实际执行：conanfile.py
build() 内 `BUILD_TEST=ON` 构建 + 构建树签名后逐项运行（LD_LIBRARY_PATH 指向
构建树与依赖包 lib 目录）。两个工程性 skip，均在日志中显式披露：

- `test_deserialize.bin`：上游硬编码开发者本机路径 `/home/suilingzhi/resnet50.xmodel`，
  无样例模型随源码分发；
- `test_subgraph_topo.bin`：依赖外部 graphviz `dot` 二进制（save_to_dot→dot 渲染），
  OHOS 设备无 graphviz。配方内以 no-op dot shim（PATH 前置）使图逻辑断言真实
  执行，渲染输出为空文件，已在日志披露。

### 3. 统计回填（如实申报）

| 指标 | 值 |
|---|---|
| 上游测试命令 | `cmake --build build-ohos; ./test/test_*.bin`（配方内签名后逐项执行） |
| 用例总数 | 11 |
| 通过 / 失败 / 跳过 | **9 / 0 / 2** |
| 标记 | `HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "discovered": 11, "executed": 9, "passed": 9, "failed": 0, "skipped": 2}`（conan-create.log:544-545） |

逐项结果（`reports/upstream-test.log`）：

```
[pass] demo.bin
[skip] test_deserialize.bin: hardcoded developer-local xmodel path, no sample model shipped upstream
[pass] test_deserialize_model.bin        （输入由配方 fixture gen_xmodel.cpp 生成）
[pass] test_graph_impl.bin
[pass] test_graph_iso.bin
[pass] test_graph_template.bin
[pass] test_md5sum.bin
[pass] test_subgraph.bin
[pass] test_subgraph_iso.bin
[pass] test_subgraph_tensors_sort.bin
[skip] test_subgraph_topo.bin: requires external graphviz 'dot' binary (not available on OHOS device/ohpcd)
SUMMARY: {"status": "passed", ..., "discovered": 11, "executed": 9, "passed": 9, "failed": 0, "skipped": 2}
```

## 二、鸿蒙消费者用例（新增，test_package/test.cpp）

命令：`./test_xir hmbs_consumer.xmodel`（conan create 的 test() 阶段在本机
OHOS PC 上**真实执行**，conanrun env，test_xir 已剥 .codesign 后 selfSign）

| 指标 | 值 |
|---|---|
| 检查项总数 | 2（op 数量校验 + op 名称往返校验） |
| 通过 | 2 |
| 失败 | 0 |
| 退出码 | 0 |

```
HMBS xir consumer test passed: serialize/deserialize round-trip OK (…/hmbs_consumer.xmodel)
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 1, "passedCount": 1}
```

覆盖面：C++ 消费者路径（Graph::create → add_op(data/const/conv2d) →
serialize(xmodel) → Graph::deserialize → get_root_subgraph → get_op_num/
has_op 校验往返一致），真实链接 libxir.so + libunilog.so（依赖闭包含
glog/gflags/boost），覆盖 xir 公共头 include 链（attrs.hpp → UniLog.hpp →
glog）的消费者编译语义。

## 三、conan create 证据

- `Package 'b6e8528ca3e890b103a3283df428461f8a8b131b' created`（reports/conan-create.log:598）
- 主包构建 65 目标全过；错误扫描 0（最终 round 28 一份日志完整证据链）
- 依赖 unilog/2.5、boost/1.85.0、protobuf/21.12、glog/0.7.1、gflags/2.2.2、
  zlib/1.3.1 二进制全部缓存/制品仓可消费（W0 `conan download` 前置全绿），
  无依赖缺失绕过
