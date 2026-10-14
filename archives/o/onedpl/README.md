# onedpl

## 简介

oneDPL（oneAPI Data Parallel Library）：header-only 的并行 STL 算法库，
后端可选 TBB / OpenMP / SYCL / serial。

## OHOS 适配

- 本仓库 `2022.12.0` 版本选用 serial 后端：零三方依赖，无需 SYCL 编译器与 oneTBB；
  par 策略降级为串行执行，API 覆盖完整。
- 上游 856 个测试中 570 个需 DPC++ 后端（OHOS 无 SYCL，不注册）；
  serial 配置注册 292 个 ctest 条目，配方在 `build()` 中完整构建并运行。

## 依赖

无
