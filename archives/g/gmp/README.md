# GMP (GNU Multiple Precision Arithmetic Library)

## 简介
GMP 是 GNU 高精度数学运算库，提供任意精度的整数、分数和浮点数运算功能。

## 基本信息
- 官网: https://gmplib.org/
- 源码: https://ftp.gnu.org/gnu/gmp/
- 许可证: LGPLv3 / GPLv2
- 构建系统: autotools

## 已编译版本
- 6.3.0 (published)
- 6.3.0.1 (2026-07-30, built，尚未发布)

## 依赖
无外部依赖（纯 C 实现）

## 使用方式
```bash
# 合入并由正式发布流水线上传后安装 Conan 包
conan install --requires=gmp/6.3.0.1 -r=ohpcd

# 编译链接
clang -fuse-ld=bfd your_program.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lgmp
```
