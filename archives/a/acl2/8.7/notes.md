# 编译笔记 — acl2 8.7

**软件名称**: acl2 (A Computational Logic for Applicative Common Lisp)
**版本**: 8.7
**编译日期**: 2026-07-15
**编译状态**: failed (缺少宿主 Lisp 编译器)

---

## 软件简介

ACL2 是一个定理证明器和一种用于推理 Common Lisp 子集程序的逻辑系统。它由 Matt Kaufmann 和 J Strother Moore 开发，是 Boyer-Moore 定理证明器（Nqthm）的继任者。

ACL2 环境由两部分组成：
1. **ACL2 系统** — 定理证明器核心，由 ACL2 作者维护
2. **Community Books** — 开源库集合，由社区维护

**源码地址**: https://github.com/acl2-devel/acl2-devel/releases/download/8.7/acl2-8.7.tar.gz
**上游仓库**: https://github.com/acl2/acl2

---

## 构建系统

- **类型**: GNU Makefile (GNUmakefile)
- **构建命令**: `make large LISP=sbcl`
- **输出**: `saved_acl2` 可执行文件（Lisp 镜像）
- **默认 Lisp**: CCL (Clozure Common Lisp)，可通过 `LISP=` 变量指定

---

## 编译过程

### 1. 源码下载

```bash
curl -fsSL -o acl2-8.7.tar.gz \
  https://github.com/acl2-devel/acl2-devel/releases/download/8.7/acl2-8.7.tar.gz
```

- 源码包大小: ~237 MB (包含 ACL2 系统和 community books)
- SHA256: `370433766f56737e597b09c0fd8f837d2df889ec8ed51efa9fc869a93185ce89`

### 2. 构建步骤

ACL2 的构建过程需要在构建系统上安装 Common Lisp 编译器：

```bash
# 安装 SBCL (Steel Bank Common Lisp)
# 注意：请在执行前检查脚本内容，确保来源可信
INSTALL_SH=$(mktemp)
curl -fsSL -o "$INSTALL_SH" https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh
# 可选：检查脚本内容后再执行
# cat "$INSTALL_SH"
sh "$INSTALL_SH" sbcl
rm -f "$INSTALL_SH"

# 构建 ACL2
cd acl2-8.7
make large LISP=sbcl
```

构建完成后生成 `saved_acl2` 可执行文件。

### 3. 测试

ACL2 自带测试套件：
- `make mini-proveall` — 最小证明测试
- `make regression` — 完整回归测试（认证 community books，耗时数小时）

test_package 中的烟雾测试验证：
1. `saved_acl2` 文件存在且可执行
2. 能运行简单的 ACL2 证明会话 `(thm (equal (+ 1 1) 2))`

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 Common Lisp 编译器 | OHOS 平台无预装 SBCL/CCL | 需先为 OHOS aarch64 交叉编译 SBCL |
| 2 | 源码包体积大 | 包含 community books (~237MB) | CI 构建可能需要较长下载时间 |
| 3 | 构建耗时长 | ACL2 需要编译大量 Lisp 源文件 | 预期首次构建 30-60 分钟 |

---

## 依赖说明

| 依赖 | 类型 | 说明 |
|------|------|------|
| SBCL | 构建依赖 | Steel Bank Common Lisp，ACL2 的宿主 Lisp 编译器 |
| GNU Make | 构建工具 | 需要 GNU make (gmake) |

### SBCL 依赖链

ACL2 → SBCL → C 编译器 (clang)

SBCL 本身是一个 C+Lisp 项目，需要先在 OHOS 上编译 SBCL，然后才能构建 ACL2。

---

## 验证结果

- **编译状态**: failed (缺少 SBCL)
- **submit --check**: 未执行（缺少构建环境）
- **conan-verify**: 未执行（缺少构建环境）
- **本地 CI 模拟**: 未执行（缺少构建环境）

> 当前环境缺少 OHOS aarch64 构建环境和 SBCL 编译器，无法完成实际编译。
> Conan 配方已按仓库规范编写，待 SBCL 在 OHOS 上可用后即可执行构建。

---

## 补丁说明

本次适配无需补丁。ACL2 的 GNUmakefile 构建系统具有良好的可移植性，
通过 `LISP=` 变量即可指定宿主 Lisp 编译器路径。

---

## 注意事项

1. ACL2 不是传统的 C/C++ 库，而是基于 Common Lisp 的定理证明器
2. 构建产物 `saved_acl2` 是一个自包含的 Lisp 镜像，不是 .so/.a 文件
3. Community books 目录 (`books/`) 包含大量 Lisp 源文件，体积较大
4. 完整回归测试 (`make regression`) 耗时数小时，CI 中仅运行烟雾测试

---

**编译结束**: 2026-07-15
**最终状态**: failed (等待 SBCL 可用后重试)
