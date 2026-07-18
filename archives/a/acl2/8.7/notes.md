# 编译笔记 — acl2 8.7

**软件名称**: acl2 (A Computational Logic for Applicative Common Lisp)
**版本**: 8.7
**编译日期**: 2026-07-18
**编译状态**: failed (CI #6701 缺少宿主 Lisp；修复后待重跑)

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
- **构建命令**: `MAKEFLAGS=-j1 make -j1 large LISP=<host-lisp>`
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

ACL2 的构建过程需要可在构建机上运行的 Common Lisp。配方优先使用已有的 SBCL 或 CCL；CI 未提供时，从 GNU 官方源码构建 GCL 2.7.1：

```bash
curl -fsSL -o gcl-2.7.1.tar.gz https://ftpmirror.gnu.org/gcl/gcl-2.7.1.tar.gz
printf '%s  %s\n' \
  79d0bb65b82df81c078bc55c4cda3fe4d766d87e3bfe10fde0b2f728204e1015 \
  gcl-2.7.1.tar.gz | sha256sum -c -
tar -xzf gcl-2.7.1.tar.gz
cd gcl-2.7.1
./configure --enable-ansi=yes --enable-xgcl=no --enable-readline=no \
  --enable-dynsysgmp=no --enable-locbfd=yes --disable-statsysbfd
MAKEFLAGS=-j1 make -j1

cd ../acl2-8.7
MAKEFLAGS=-j1 make -j1 large LISP=../gcl-2.7.1/unixport/saved_gcl
```

OHOS 构建中，GCL 各引导阶段生成的 ELF 镜像以及最终 `saved_acl2` 必须在首次运行前移除旧 `.codesign`、重新自签并恢复执行权限。该流程已由配方和补丁自动执行。

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
| 1 | 缺少 Common Lisp 编译器 | OHOS CI 无预装 SBCL/CCL | 配方从 GNU 官方源码引导 GCL 2.7.1 |
| 2 | 源码包体积大 | 包含 community books (~237MB) | CI 构建可能需要较长下载时间 |
| 3 | 构建耗时长 | ACL2 需要编译大量 Lisp 源文件 | 预期首次构建 30-60 分钟 |
| 4 | 引导生成的 ELF 无法执行 | OHOS 要求新生成 ELF 具有有效代码签名 | 在 GCL 各引导阶段和 ACL2 打包前执行自签名 |

---

## 依赖说明

| 依赖 | 类型 | 说明 |
|------|------|------|
| GCL 2.7.1 | 构建依赖 | CI 缺少 SBCL/CCL 时从源码引导的宿主 Lisp |
| GNU Make | 构建工具 | 需要 GNU make (gmake) |

### GCL 引导链

ACL2 → GCL 2.7.1 → C 编译器 (clang)

---

## 验证结果

- **编译状态**: failed (CI #6701 未找到 Common Lisp 实现)
- **静态检查**: 配方语法、YAML、补丁适用性和 Conan inspect 已验证
- **OHOS 真机构建**: 已增加 GCL 引导修复，待 PR CI 重跑验证完整构建

> 当前 Windows 环境无法执行 OHOS aarch64 真机构建。配方不再依赖 CI 预装 SBCL/CCL，并通过固定版本和 SHA256 的 GCL 2.7.1 完成宿主 Lisp 引导。

---

## 补丁说明

本次增加 GCL bootstrap 补丁，在每个新生成 Lisp ELF 镜像首次执行前完成 OHOS 自签名。ACL2 本身无需源码补丁，通过 `LISP=` 指定 GCL 路径。

---

## 注意事项

1. ACL2 不是传统的 C/C++ 库，而是基于 Common Lisp 的定理证明器
2. 构建产物 `saved_acl2` 是一个自包含的 Lisp 镜像，不是 .so/.a 文件
3. Community books 目录 (`books/`) 包含大量 Lisp 源文件，体积较大
4. 完整回归测试 (`make regression`) 耗时数小时，CI 中仅运行烟雾测试

---

**编译结束**: 2026-07-18
**最终状态**: failed (已修复宿主 Lisp 缺失问题，待 CI 重跑)
