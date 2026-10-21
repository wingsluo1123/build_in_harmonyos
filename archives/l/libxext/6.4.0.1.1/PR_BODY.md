# 【依赖项】feat(libxext): 6.4.0.1.1 依赖变体补发（libx11/1.8.13 force=True，闭环 libxmu 下游依赖）

- **三方库名称**：libxext（X.Org 扩展库，构建 `libXext.so.6.4.0`）
- **上游版本**：6.4.0.1.1（Conan 包名映射上游 libXext 1.3.6；`.1.1` 是本仓配方修订号，上游源码 tarball 与 sha256 不变）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libXext
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent
- **适配分支 / HEAD**：`feat/libxext-6.4.0.1.1`

## 变更说明（依赖变体补发）

**背景**：`libxmu/1.3.1.1` 通过 `force=True` 将全依赖图 libx11 钉在 `1.8.13`（libx11/1.8.13 的 package() 保留 `libX11.la`，供 libxt 的 `_prepare_ohos_libtool_shadow()` 使用；libx11/6.4.0 的 package() 会 `rm("*.la")`）。因此经 libxmu 的下游（如 zutty）解析 libxext 时要求其基于 libx11/1.8.13 的二进制变体（package id `eab79208...`）。

**问题**：制品仓中 libxext/6.4.0.1 只发布了基于 libx11/6.4.0 的变体（`e647863c...`，2026-09-01 发布时依赖图未含 force 1.8.13 的 libxmu），缺失 `eab79208...` 变体 → 下游 CI 无法下载匹配二进制，被迫从源码构建 libxext → 构建/资源失败（如 PR #16371 zutty 的 CI #97659）。

**本 PR 修复**：**递增版本号**至 `libxext/6.4.0.1.1`（cnb.cool 制品仓不支持同版本多 recipe revision，R37 门禁要求递增版本后缀；已发布 6.4.0.1 配方保持原状），新配方 `requirements()` 将 libx11 从 `6.4.0` 改为 `1.8.13` 并加 `force=True`（与 libxmu 口径一致），使 CI 构建并发布基于 libx11/1.8.13 的 `eab79208...` 变体，闭环下游依赖。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | libXext 1.3.6 无独立测试套件 |
| 集成测试 | 0 | - |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 1 | 不变 | `test_package/test.c` 链接 libXext 并验证 XShm 头文件/符号 |
| **合计** | **1** | 不变 | |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例（本 PR 仅调整依赖声明，不改源码/测试）

## 补全测试用例说明

- [x] **否**，上游无测试用例（纯库包，test_package 消费者测试覆盖链接与头文件可用性）

## 验证结果

- 编译状态：待 CI 实跑回填（本地 `conan graph info` 确认依赖图解析出目标变体 `eab79208...`，完整构建由 CI 执行）
- 上游测试用例通过率：N/A（上游无测试）
- 新增测试用例通过率：待 CI 实跑回填（test_package 消费者测试）

## 补充说明

- **变更范围**：新增 `archives/l/libxext/6.4.0.1.1/`（conanfile.py requires 段 + conandata.yml 版本键 + manifest.yaml + test_package 版本引用），`archives/l/libxext/6.4.0.1/`（已发布版本）保持原状。
- **依赖变体机制**：同一 Conan recipe 可产出多个 package id（不同 requires 版本线）。本 PR 让 libxext 在 libx11/1.8.13 线上构建发布新版本（6.4.0.1.1），与既有 6.4.0.1 的 6.4.0 变体（e647）共存于制品仓，不破坏既有消费者。
- **参考**：libxmu/1.3.1.1 配方同款 force 注释；Issue #3545（libXft 硬 pin libx11/1.8.Z 先例）；知识库 E1509/E1520（依赖闭包变体补发必须递增版本号）。
