- **三方库名称**：dbg-macro
- **上游版本**：0.5.1
- **上游仓库地址**：https://github.com/sharkdp/dbg-macro
- **适配路径**：路径 A（基础适配，同版本重验证）
- **使用知识库**：无（header-only，零依赖，CMake 原生兼容）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 18 | 来源：`tests/basic.cpp`，9 个 Catch2 `TEST_CASE` 分别以正常宏和 `DBG_MACRO_DISABLE` 两种配置编译 |
| 其他测试 | 1 | 来源：`tests/demo.cpp`，上游注册为 `dbg_macro-demo` CTest 运行检查 |
| **合计** | **19** | CTest 条目总数（0.5.1.1 归档同口径，同一上游 tarball） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 19 | 不变 | macOS 实跑 19/19；OHOS CI #86325 已编译上游套件，执行清点时 Python 直接启动 `ctest` 报 `FileNotFoundError`，上游实际执行 0/19 |
| 消费者测试 | 1 | 新增 | 消费者程序通过安装后的 `dbg_macro::dbg_macro` 验证 6 项公开 API 行为；OHOS CI #86325 已运行 6/6 |
| **合计** | **20** | **+1** | 声明上游 19 条目与消费者 1 个程序；平台实跑结果分别列示 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，消费者测试本次补强

> - **补全的测试范围**：`test_package/test.cpp` 6 项检查（dbg() 返回值/多参数、pretty_print(vector)、dbg::hex、dbg::bin），口径与 0.5.1.1 一致
> - **补全原因**：覆盖头文件公开的格式化 API
> - **新增测试文件清单**：
>   1. `archives/d/dbg-macro/0.5.1/test_package/test.cpp` — 6 项检查（macOS arm64 clang C++11/C++17 双档实测通过）

## 验证结果

- 编译状态：本轮 macOS 原生构建通过；[OHOS CI #86325](https://ohpcd.atomgit.com/ci?id=86325) 上游与消费者编译成功，但 `test_package` 在清点上游时失败。版本级 `conanfile.py`/`conandata.yml` 保持逐字节不变。
- 上游测试用例通过率：修复后本轮 macOS CTest 19/19（100%）；OHOS CI #86325 实际执行 0/19（清点命令无法启动，因此无上游通过率）。
- 新增测试用例通过率：本轮 macOS arm64 clang C++11/C++17 均 6/6（100%）；OHOS CI #86325 消费者已执行 6/6（100%）。
- 修复回归：先复现原 `FileNotFoundError`，再真实使用 Conan 2.33 命令入口执行完整上游套件；另验证清点命令失败、无总数、少于 19 项、测试执行失败均使测试失败。该回归模拟了 Python 直接执行的故障边界，不能替代 OHOS 真机复验。

## 补充说明

- CI 故障修复：`ctest -N` 改用 `self.run(stdout=StringIO(), env="conanbuild")`，CTest 实跑也使用同一构建环境，删除 Python 侧 `shutil.which` 预检。命令启动失败或非零退出仍直接失败，清点必须严格等于 19 项，不新增跳过路径。
- rule4 的 OHOS 19/19 运行要求尚未闭环：当前目标机证据仍是 #86325 清点失败；修复版本需新一轮 OHOS CI 确认。rule7 已有该轮 CI 记录。
- 上游 tarball 缺 Catch2 submodule 的历史原因与钉版恢复方案见 0.5.1.1 归档；两版本归档互补
