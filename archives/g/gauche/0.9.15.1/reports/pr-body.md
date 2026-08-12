## PR 信息
- **三方库名称**：Gauche
- **上游版本**：0.9.15
- **上游仓库地址**：https://github.com/shirok/Gauche
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 125 个测试脚本文件 | 来源：Gauche 0.9.15 源码中名称匹配 `test*.scm` 或 `*test*.scm` 的测试脚本；上游统一入口为 `make check` |
| 集成测试 | 0 | 上游源码未单独提供可在本适配环境中统计的集成测试分类 |
| 其他测试 | 0 | 未将示例程序计入测试用例 |
| **合计** | **125 个测试脚本文件** | 已尝试完整上游 `make check`，但配置阶段被当前 HMDFS 临时目录权限和缺少 mbedTLS 依赖阻断，未进入测试执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-------------|------|
| 单元测试 | 0 已执行 | 未形成可比通过率 | 上游完整测试入口未能通过配置阶段，未虚报执行结果 |
| 集成测试 | 0 | 不变 | 无独立集成测试分类 |
| 鸿蒙特有测试 | 1 | 新增 | Conan `test_package` 的 `test_gauche` consumer test，验证 `gosh`、头文件和 Gauche 库链接/运行 |
| **合计** | **1 个已执行测试** | 新增 1 | `test_gauche`：1/1 Passed |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

适配补丁仅修改 OHOS 构建、Boehm GC 兼容性、安装流程和生成构建文件相关路径；没有修改上游测试脚本。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游完整测试无法在当前 OHOS 构建环境中执行，适配后补充了 consumer test

- **补全的测试范围**：1 个 Conan consumer test，覆盖可执行文件运行、Gauche 头文件包含和库链接
- **补全原因**：上游 `make check` 在当前环境的配置阶段受 HMDFS 私有临时目录权限和缺少 mbedTLS 阻断；需要至少保留可执行的包级功能验证，且不将其冒充为上游完整测试
- **新增测试文件清单**：
  1. `archives/g/gauche/0.9.15.1/test_package/test.c` — consumer test，验证 Gauche 运行时/库的基本可用性
  2. `archives/g/gauche/0.9.15.1/test_package/conanfile.py` — Conan test package 构建与测试入口

---

## 验证结果

- **编译状态**：通过
- **上游测试用例通过率**：0/125（0%：未进入执行阶段；配置被环境权限和缺少 mbedTLS 阻断）
- **新增测试用例通过率**：1/1（100%）

### 已实际执行的验证命令

```text
conan create archives/g/gauche/0.9.15.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

python3 scripts/ohc/ohc-run.py verify-build gauche 0.9.15.1
```

结果：Conan 包创建成功；`test_gauche` 为 `1/1 Passed`；G1/G2/G3/G4 及 W3 通过。

上游测试尝试：

```text
TMPDIR=<writable-project-temp> \
Gauche-0.9.15/configure \
  --build=aarch64-unknown-linux-gnu \
  --disable-tls --disable-gdbm --disable-dbm
make -j2 check
```

结果：配置阶段失败，当前 HMDFS 无法创建 configure 的私有临时目录；同时环境没有 mbedTLS headers/libraries。`make check` 因此未启动。

---

## 补充说明

- CI 源码获取使用公开 GitCode 镜像仓库的固定 commit：`14895b1875d56a2d4ef5b90e6035b45c44041d7e`；镜像内嵌的官方 `Gauche-0.9.15.tgz` 仍以官方 SHA-256 `3643e27bc7c8822cfd6fb2892db185f658e8e364938bc2ccfcedb239e35af783` 校验。
- 适配补丁未修改上游测试文件。
- 已生成并验证 OHOS aarch64 release/debug 打包产物。
- 本 PR 不声称上游完整测试通过；建议 CI 环境提供可写私有临时目录和 mbedTLS 后重新运行 `make check`。
