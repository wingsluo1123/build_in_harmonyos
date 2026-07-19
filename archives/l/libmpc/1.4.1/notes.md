# libmpc 1.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 使用 harmonybrew 的 GMP 和 MPFR
./configure --prefix=$DEFAULT_PREFIX \
  --with-gmp=/storage/Users/currentUser/.harmonybrew/Cellar/gmp/6.3.0 \
  --with-mpfr=/storage/Users/currentUser/.harmonybrew/Cellar/mpfr/4.2.2
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml sha256 占位符 | conan-init 生成时未计算 | 用 sha256sum 计算真实值 |
| 2 | manifest.yaml 模板占位符 | conan-init 生成时未填充 | 手动填写 software, build_system, sha256, tar_format |
| 3 | package_info libs 错误 | 模板将 name 直接用于 libs | libs 应为 ["mpc"] (去 lib 前缀) |
| 4 | GMP/MPFR 依赖 | 非 Conan 包 | 在 generate() 中用 --with-gmp/--with-mpfr 指向系统库 |
| 5 | test_package 空壳测试 | 模板生成默认 test.c 只打印字符串 | 编写调用 MPC API 的真实测试 (R34) |

## 源码修改

无补丁。libmpc 1.4.1 在 HarmonyOS 上原生编译通过。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| GMP | 6.3.0 | harmonybrew |
| MPFR | 4.2.2 | harmonybrew |

## 验证结果

```bash
# conan-verify 通过 (G0-G4 + L2/L4/L5)
python3 ohc-run.py conan-verify libmpc 1.4.1
```

## 注意事项

- GMP 和 MPFR 不是 Conan 包，使用系统安装的 harmonybrew 版本
- test_package 的 CMakeLists.txt 需要显式查找 GMP 和 MPFR 库路径
- library package_type，不需要 commands.json (R38)
---

**编译结束**: 2026-07-19 13:01
**最终状态**: built
