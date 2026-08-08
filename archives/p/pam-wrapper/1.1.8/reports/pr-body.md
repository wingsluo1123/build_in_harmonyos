# 建议 PR 标题

`【高难度挑战】feat(pam-wrapper): 1.1.8 适配 HarmonyOS PC`

## PR 信息

- **三方库名称**：pam-wrapper
- **上游版本**：1.1.8
- **上游仓库地址**：https://gitlab.com/cwrap/pam_wrapper
- **官方源码地址**：https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz
- **关联 Issue**：#1763
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）+ 路径 C（高难度挑战候选）
- **使用知识库**：E077、E200、E223 draft；新增两个 pam-wrapper 配套草稿
- **高难举证**：`archives/p/pam-wrapper/1.1.8/reports/high-difficulty-evidence.md`

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 23 | `tests/test_pam_wrapper.c`，由 CTest/CMocka 驱动 |
| 集成测试 | 0 | 上游未单列其他自动测试入口 |
| 其他测试 | 0 | Python 测试因未启用 binding 不计入本配置 |
| **合计** | **23** | 1 个 CTest target 内 23 个独立 CMocka case |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 23 | 不变 | 目标端 23/23 PASS，未修改 case 和期望值 |
| 集成测试 | 1 | +1 | 安装包 consumer 完成 `dlopen`、`libpamtest` 和 `pam_matrix` 认证 |
| 鸿蒙特有测试 | 0 | 不变 | 签名与启动环境是执行前置，不拆分计为测试 |
| **合计** | **24** | **+1** | 不按内部断言、重复运行或构建模式扩充计数 |

## 上游测试用例修改说明

- [x] **否**，未修改上游 `tests/test_pam_wrapper.c` 的 case、输入或预期结果。
- 四份 patch 只调整 CMake 的 PAM include/library 路径，使 configure、库、MODULE
  和上游测试目标绑定同一个 Conan `linux-pam/1.7.2` 包。
- 配方默认开启 `UNIT_TESTING`，将 `cmocka/2.0.2` 作为 `test_requires`，在 CTest
  前处理实际参与运行的 build-tree ELF。

## 补全测试用例说明

- [x] **是**，新增 1 个安装包消费者流程。
- **补全范围**：验证已安装 `libpam_wrapper.so`、`libpamtest.so`、
  `pam_matrix.so`、PAM service 和 passdb 的完整联动。
- **新增文件**：`test_package/test_pam_wrapper.c`。
- **关键边界**：Conan `test()` 在启动消费者前创建 service/passdb，并通过同一次
  `exec` 设置 `LD_PRELOAD`、`LD_LIBRARY_PATH`、`PAM_WRAPPER_SERVICE_DIR` 和
  `PAM_WRAPPER_RUNTIME_DIR`。只验证 `dlopen` 不足以判定通过。

## 验证结果

### 编译验证

- 编译器：HarmonyOS Clang / aarch64
- 编译状态：通过
- 构建系统：CMake + Conan 2
- 默认配置：`shared=True, with_upstream_tests=True, UNIT_TESTING=ON`

### 产物与运行验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | PASS | `conan create` 完成 |
| 产物存在性 | PASS | `libpam_wrapper.so`、`libpamtest.so` 和 PAM modules 已安装 |
| ELF 签名 | PASS | build-tree 测试图和 package `.so` 均在运行前处理 |
| 上游测试 | PASS | 1/1 CTest target，23/23 CMocka cases |
| 消费者测试 | PASS | 输出 `pam-wrapper libpamtest authentication check passed` |
| 仓库 CI | PASS | L0/L1/L4/L5 PASS；library package 无 `bin/`，L2 正常跳过 |

### 补丁说明

1. `0001-ConfigureChecks.cmake.patch`：让 PAM 头检查使用 Conan include，并兼容
   libc 内建 `dlopen` 时无独立 `libdl`。
2. `0002-src-CMakeLists.txt.patch`：为 `pam_wrapper`/`pamtest` 注入 PAM 头和库路径。
3. `0003-src-modules-CMakeLists.txt.patch`：为 PAM MODULE 目标注入相同依赖路径。
4. `0004-tests-CMakeLists.txt.patch`：让上游 CMocka test target 使用相同 PAM 依赖。

### 依赖

- 运行依赖：`linux-pam/1.7.2`
- 测试依赖：`cmocka/2.0.2`（`test_requires`，不进入运行时依赖合同）

### 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 上游系统 PAM 查找不稳定 | legacy CMake 变量未绑定 Conan 包 | 从 `self.dependencies` 注入精确 include/library 路径 |
| 消费者认证依赖启动前状态 | preload 库在 `main()` 前复制环境 | launcher 预创建夹具并带完整环境启动进程 |
| 上游 CTest 目标端不能直接执行 | build-tree executable/shared MODULE 需要有效签名 | 测试前枚举真实 ELF，移除旧签名并重新签名，失败即阻断 |
| 上游测试原为 opt-in | 默认包不能证明测试闭环 | 默认开启 `with_upstream_tests` 并使用 CMocka test requirement |

## 知识库补充

新增配套草稿：

- `knowledge/graph/draft/DRAFT-pam-wrapper-ctest-elf-runtime-closure.{kv,md}`
- `knowledge/graph/draft/DRAFT-pam-wrapper-preload-startup-context.{kv,md}`

两个主题分别覆盖 CTest 前构建树完整 ELF 加载闭包的签名边界，以及 `LD_PRELOAD`
库在 `main()` 前捕获配置时的测试生命周期。后者由 launcher 预创建夹具，在
`exec` 环境中一次性注入变量，并以真实拦截操作验证。草稿不修改正式索引，等待
知识库主编审核。

## 高难度挑战候选说明

本 PR 的难点不是 patch 行数，而是让多动态目标 PAM 图、Conan 精确依赖、
pre-main interposition、目标端 ELF 签名和完整上游 CMocka 套件在同一真机流程中
闭环。详细证据、计数规则和不申报边界见：

`archives/p/pam-wrapper/1.1.8/reports/high-difficulty-evidence.md`

申请纳入 Path C 高难度挑战库候选，最终等级和分值以评审结论为准。

## 证据

- CTest 日志 SHA-256：`9660199e69663db0bcced0d4bf802d3d6e318219030ecad4e731bd7806c9ed87`
- 仓库 CI 日志 SHA-256：`a181e7753188788ad47bd24a4196d2d68e47208a377d4949a9ba3370283d59c7`
- Conan verify 报告 SHA-256：`8c5d26bc22cc70ec7371e01ebd55639cb59a7ebc879a87aaf1731294e4b7a50e`

## 验证命令

```sh
conan create archives/p/pam-wrapper/1.1.8
CI_PACKAGES="archives/p/pam-wrapper/1.1.8" zsh ci/conan/build_and_test.sh
```
