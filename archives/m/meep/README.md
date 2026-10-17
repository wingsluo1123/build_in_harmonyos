# Meep

**描述**: Meep — finite-difference time-domain (FDTD) electromagnetic simulation library.

## 软件信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.29.0 |
| 构建系统 | autotools (configure/make) |
| 许可证 | GPL-2.0-or-later |
| 类别 | scientific-lib (physics/electromagnetics) |
| 源码 | https://github.com/NanoComp/meep/releases/download/v1.29.0/meep-1.29.0.tar.gz |

## 平台兼容性

✅ OpenHarmony (aarch64-unknown-linux-ohos)

- C/C++ 库，依赖 Conan 管理的 libctl/harminv/fftw/hdf5/gsl/openblas/lapack
- 无 Python/Scheme/MPI 接口（OHOS 适配时禁用）
- musl namespace 阻止 conftest 执行 → 配置脚本打补丁跳过
- 无 Fortran 编译器 → 配置脚本移除 Fortran 段
- safe-delete rm shim shebang 损坏 → 替换为 /bin/rm + shell function override

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.29.0 | built | 2026-10-12 |
