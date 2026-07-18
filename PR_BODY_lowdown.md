<!--
PR 标题：feat(lowdown): 3.0.1 适配 HarmonyOS PC
-->

## PR 信息
- **三方库名称**：lowdown
- **上游版本**：3.0.1
- **上游仓库地址**：https://github.com/kristapsdz/lowdown
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（自动适配，未命中知识库）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 无单元测试框架 |
| 集成测试 | 0 | 上游仅提供示例代码，无正式测试框架 |
| 其他测试 | 0 | — |
| **合计** | **0** | |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | — |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.c — 验证 lowdown 基本 Markdown 转换功能 |
| **合计** | **1** | **+1** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
- [ ] 是，存在对上游测试用例的修改（请在下方逐条说明）

### 补全测试用例说明

上游是否存在无测试用例，适配后补全的情况？
- [ ] 否，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

**补全的测试范围**：为核心功能新增 1 个 test_package 测试套件，验证 lowdown 基本 Markdown 转换功能。

**补全原因**：上游库仅包含示例代码，无正式测试框架。

**新增测试文件清单**：
1. `archives/l/lowdown/3.0.1/test_package/CMakeLists.txt` — 定义 test_package 构建与运行规则
2. `archives/l/lowdown/3.0.1/test_package/test.c` — 验证 lowdown 基本转换功能，修复内存泄漏问题，确保在 OHOS 平台无内存泄漏

---

## 验证结果

- **编译状态**：通过
- **上游测试用例通过率**：0/0（无上游测试用例）
- **新增测试用例通过率**：1/1（100%）

---

## 补充说明

- **编译器**：clang 15.0.4（OHOS SDK，aarch64-unknown-linux-ohos）
- **构建系统**：oconfigure（自定义 configure，KEY=value 语法）+ GNUmakefile
- **配置选项**：`CC=clang PREFIX=... shared=False`
- **编译产物**：lowdown（875KB）、lowdown-diff（875KB）、liblowdown.a（1.3MB）、lowdown.h
- **动态依赖**：静态链接，无外部动态依赖
- **补丁**：无外部补丁文件。conanfile.py 中自动处理以下兼容性问题：
  - BSD make（`.ifdef`/`.endif`）语法自动转换为 GNU make 语法
  - HMDFS 文件系统硬链接限制 → 使用 `cp -f` 替代 `ln -f`
  - HMDFS chmod 限制（E046）→ 使用 `/system/bin/sh ./configure` 显式调用
  - 缺少 sed 命令 → 使用 Python 生成 lowdown.pc