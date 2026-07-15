# CDO (Climate Data Operators)

## 简介
CDO 是气候数据领域的标准命令行工具集，支持 NetCDF 3/4、GRIB 1/2、
SERVICE、EXTRA 等格式的读取、处理、分析和可视化。

## 主要功能
- 格式转换（GRIB↔NetCDF↔SERVICE 等）
- 数据选择与提取（时间、空间、变量）
- 统计计算（均值、方差、回归等）
- 网格操作（插值、重网格、合并）
- 算术运算（表达式计算）

## OHOS 适配
- 构建系统：autotools
- 目标架构：aarch64-linux-ohos
- 静态编译，无外部依赖

## 依赖
- 可选：netCDF、HDF5、szlib（通过 --without-* 禁用）

## 功能验证
```bash
$HOME/usr/local/bin/cdo --version
$HOME/usr/local/bin/cdo --help
```

## 参考
- 主页：https://code.mpimet.mpg.de/projects/cdo
- 源码：https://github.com/ClimateDataOps/CDO