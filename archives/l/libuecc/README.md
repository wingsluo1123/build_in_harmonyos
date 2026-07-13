# libuecc

## 简介

libuecc 是一个非常小巧的椭圆曲线加密（ECC）库，专注于 Curve25519 曲线。它由 Matthias Schiffer 开发，主要用于 fastd（Fast and Secure VPN Daemon）项目。

## 特点

- 极小的代码体积，适合嵌入式和资源受限环境
- 专注于 Curve25519（Ed25519）曲线运算
- 纯 C 实现，无外部依赖
- 提供静态库和共享库两种构建模式
- MIT 许可证

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 7 | published | 2026-06-26 |

## 构建

- **构建系统**: CMake
- **编译器**: clang 15.0.4
- **平台**: OpenHarmony aarch64
- **依赖**: 无

## API

主要提供的函数（均在 `ecc.h` 中声明）：

- `ecc_25519_load_xy_ed25519()` / `ecc_25519_load_xy_legacy()` — 加载坐标点
- `ecc_25519_store_xy_ed25519()` / `ecc_25519_store_xy_legacy()` — 存储坐标点
- `ecc_25519_load_packed_ed25519()` / `ecc_25519_load_packed_legacy()` — 加载压缩点
- `ecc_25519_store_packed_ed25519()` / `ecc_25519_store_packed_legacy()` — 存储压缩点
- `ecc_25519_is_identity()` — 判断是否为单位元
- `ecc_25519_negate()` — 点取反
- `ecc_25519_double()` — 点倍乘
- `ecc_25519_add()` / `ecc_25519_sub()` — 点加/减
- `ecc_25519_scalarmult()` / `ecc_25519_scalarmult_base()` — 标量乘法
- `ecc_25519_gf_is_zero()` / `ecc_25519_gf_add()` / `ecc_25519_gf_sub()` — GF 运算

## 许可证

BSD 2-Clause License（见源码 COPYRIGHT 文件）
