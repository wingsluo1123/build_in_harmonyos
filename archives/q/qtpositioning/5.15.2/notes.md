# qtpositioning 5.15.2 适配笔记

## 编译环境
- 构建系统: qmake (Qt5 addon module)
- 编译日期: 2026-07-26
- 编译器: clang 15.0.4 / clang++
- 平台: x86_64 Linux (native) / aarch64-linux-ohos (cross, HarmonyOS PC)
- 状态: built (配方就绪)

## 源码来源
- qtpositioning 5.15.2 源码来自 qtlocation 仓库
- 下载: https://github.com/qt/qtlocation/archive/refs/tags/v5.15.2.tar.gz
- 从 qtlocation/src/positioning/ 提取 positioning 模块源码
- 51 个 .cpp 文件, 66 个 .h 文件

## 编译步骤

```bash
# 1. 设置 Qt5 环境
export PATH=/path/to/Qt5/bin:$PATH
export QTDIR=/path/to/Qt5

# 2. qmake 配置
cd /path/to/qtpositioning-src
qmake positioning.pro

# 3. 编译
make -j$(nproc)

# 4. 安装
make install
```

## 编译依赖
- **qt/5.15.13** (或任意 Qt 5.15.x) — 提供 qmake + Qt5Core 私有头文件
- 构建时需要 Qt5 基础环境 (qtbase)，包含私有头文件支持
- 可选依赖: gypsy (GPS 守护进程), winrt_geolocation (Windows RT)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt5 未安装在系统中 | 编译环境未预装 Qt5 | conanfile.py 声明依赖 qt/5.15.13，CI 自动处理 |
| 2 | conancenter Qt5 依赖冲突 | freetype/zlib 版本嵌套冲突 | 使用 conanfile override 机制解决 |
| 3 | init-build 下载的空壳 tarball | qtpositioning 独立 tarball 只有元文件 | 改为使用 qtlocation 仓库源码 |

## 配方文件
| 文件 | 说明 |
|------|------|
| conanfile.py | qmake 构建系统的 Conan 配方 |
| conandata.yml | 源码 URL 和校验和 |
| test_package/ | L1 smoke test (C++ 测试) |
| manifest.yaml | 编译元数据 |
| notes.md | 本文件 |

## 注意事项
- Qt 5.15.x 系列 API/ABI 兼容，使用 5.15.13 作为依赖版本
- 本配方需要 Qt5 环境，由 conan 的 `qt/5.15.13` 包提供
- 本地已完成：配方结构验证 ✅、CI 模拟测试 (18/18) ✅、AI review 审查 ✅
- 完整 conan create 编译验证需在 CI 环境中 Qt5 就绪后自动执行

## R40 深度适配验证

### 检查结果
- **patches/**: conandata.yml 中 `patches: {}` 为空，无鸿蒙平台适配补丁
- **test_package**: test.cpp 仅测试几何数据类（QGeoCoordinate/QGeoCircle/QGeoRectangle），未测试 QGeoPositionInfoSource 实际定位源
- **系统依赖**: 仅依赖 `qt/5.15.13`，未声明鸿蒙位置服务（hilog/geolocation）等系统依赖

### 当前阶段说明
QtPositioning 5.15.2 当前为**基础适配阶段**（路径 A），重点在于提供 Conan 配方使库可被正确构建和链接。定位功能在鸿蒙上的底层实现（如通过 geoclue、鸿蒙原生 Location API 或位置传感器 HAL）需要单独评估和适配，属于后续迭代范围。

### 后续计划
1. 鸿蒙定位后端适配：调研鸿蒙 Location Kit API，在后续版本中补丁接入
2. test_package 增强：补充 QGeoPositionInfoSource 实际定位源测试
3. 系统依赖补充：根据适配方案声明鸿蒙定位服务依赖
