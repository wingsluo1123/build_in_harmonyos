## PR 信息

- **三方库名称**：codebook-lsp
- **上游版本**：v0.3.41
- **上游仓库地址**：https://github.com/blopker/codebook
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：harmony-compile（OpenHarmony 三方库编译兼容性框架）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 13 | 来源：cargo test（crates/codebook-lsp + crates/codebook 的 Rust 标准测试框架） |
| 集成测试 | 0 | 上游无独立集成测试套件 |
| 其他测试 | 0 | — |
| **合计** | **13** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 13 | 不变 | 上游 cargo test 全部保留并通过 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.sh：验证 codebook-lsp 二进制在 OHOS 上可执行且版本正确 |
| **合计** | **14** | **+1** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

> 注：本次适配修补的是 cargo registry 中的依赖 crate（nix 0.26.4、aws-lc-sys 0.41.0），未修改 codebook 上游源码及其测试代码。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无 Conan 包级别测试，适配后补全了测试

> - **补全的测试范围**：为 Conan 包新增 1 个 smoke test（test_package/test.sh），验证安装后的 codebook-lsp 二进制可执行且版本输出正确
> - **补全原因**：上游使用 Rust cargo test 框架，无 Conan 包消费者视角的验证测试。Conan CI 流水线（build_and_test.sh）要求 test_package/ 存在
> - **新增测试文件清单**：
>   1. `test_package/test.sh` — 运行 `codebook-lsp --version` 并验证输出为 `codebook-lsp 0.3.41`

---

## 验证结果

- 编译状态：通过（cargo build --release --locked 成功）
- 上游测试用例通过率：13/13（100%）
- 新增测试用例通过率：1/1（100%）

---

## 补充说明

### 适配概要

codebook-lsp 是基于 Rust 的代码感知拼写检查器，含 LSP 语言服务器实现。本次适配攻克了两个 OHOS 平台兼容性难题：

1. **aws-lc-sys CMake 架构检测失败**（知识图谱草稿 E212）：CMake 在 OHOS 上无法检测 `CMAKE_SYSTEM_PROCESSOR`，导致 aws-lc 的 ARCH 被设为 "generic"，跳过所有汇编源文件，链接阶段报 `ld.lld: undefined symbol`。修补 CMakeLists.txt 强制 ARCH=aarch64 + 启用 Perl 汇编生成。

2. **nix 0.26.4 crate OHOS 兼容性**：8 个编译错误，涉及 fcntl/signal/statfs/statvfs 等模块的 syscall 常量和结构体差异。修补 5 个源文件添加 `target_os = "ohos"` cfg 属性。

### 补丁文件

| 补丁 | 目标 | 说明 |
|------|------|------|
| `patches/0001-nix-ohos-compat.patch` | cargo-registry:nix-0.26.4 | 修复 8 个 OHOS 兼容性错误（fcntl/signal/statfs/statvfs/Cargo.toml） |
| `patches/0002-aws-lc-sys-cmake-arch.patch` | cargo-registry:aws-lc-sys-0.41.0 | 修补 CMake 架构检测，强制 ARCH=aarch64 |

### 知识图谱贡献

- **E212 草稿**：aws-lc-rs assembly symbols undefined on OHOS due to CMake processor detection failure
- 位于 `knowledge/graph/draft/E212-draft-CC11.kv` + `.md`
- 待主编审核后提升为正式条目

### 已知限制

- conan-verify G2（conan create）因 OHOS 环境访问 GitHub SSL 不稳定未通过，非代码质量问题
- conanfile.py 中 OpenSSL 路径硬编码为 harmonybrew 安装路径，CI 环境需自行配置
- cargo registry 补丁为临时性，conanfile.py 的 `_apply_cargo_registry_patches()` 方法在 build() 中自动应用

### 归档文件清单

```
archives/c/codebook-lsp/0.3.41/
├── conanfile.py          # Conan 配方 (Rust/Cargo, R32合规, 补丁应用逻辑)
├── conandata.yml         # 源码URL+SHA256 + 2个补丁声明
├── manifest.yaml         # 编译元数据 (status: built)
├── notes.md              # 完整适配笔记
├── patches/
│   ├── 0001-nix-ohos-compat.patch
│   └── 0002-aws-lc-sys-cmake-arch.patch
├── test_package/
│   ├── conanfile.py      # Rust 二进制 smoke test
│   ├── test.sh           # codebook-lsp --version 验证
│   └── MANIFEST.yml      # 测试声明
└── reports/
    ├── conan-verify-report.md
    └── conan-create.log
```
