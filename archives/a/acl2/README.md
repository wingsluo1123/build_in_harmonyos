# acl2 — A Computational Logic for Applicative Common Lisp

## 软件简介

ACL2 是一个定理证明器（theorem prover）和一种用于推理程序属性的计算逻辑系统。
它由 Matt Kaufmann 和 J Strother Moore 开发，是 Boyer-Moore 定理证明器（Nqthm）的继任者。
ACL2 用 Common Lisp 编写，需要宿主 Lisp 编译器（SBCL/CCL）来构建。

**主要功能**:
- 数学定理证明（基于归纳法）
- 程序正确性验证
- 硬件和软件形式化验证
- 自动化和交互式证明策略

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 8.7 | failed | 2026-07-15 | 0 |

## 构建说明

- **构建系统**: GNU Make (GNUmakefile)
- **构建命令**: `make large LISP=sbcl`
- **构建依赖**: SBCL (Steel Bank Common Lisp)
- **输出**: `saved_acl2` 可执行文件

## 平台适配说明

### 鸿蒙系统适配

ACL2 的构建不涉及 C 编译，而是通过宿主 Lisp 编译器编译 Lisp 源代码。
要在 OHOS 上构建 ACL2，需要先在 OHOS 上安装 SBCL。

**关键依赖**: SBCL 需要先为 OHOS aarch64 编译。

## 源码信息

- **源码地址**: https://github.com/acl2/acl2
- **发布包**: https://github.com/acl2-devel/acl2-devel/releases
- **许可证**: ACL2 License (BSD-like)
- **维护者**: Matt Kaufmann, J Strother Moore

## 相关资源

- [GitHub 仓库](https://github.com/acl2/acl2)
- [ACL2 主页](http://www.cs.utexas.edu/users/moore/acl2)
- [编译详情](./8.7/notes.md)
