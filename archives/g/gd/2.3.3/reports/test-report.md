# Test Report — gd 2.3.3

## 编译信息
- 软件: gd 2.3.3
- 构建系统: autotools
- 编译器: clang 15.0.4
- 编译日期: 2026-07-23
- 构建状态: SUCCESS

## 编译步骤
1. 下载源码 libgd-2.3.3.tar.gz (通过 ghfast.top 镜像)
2. 应用 config.guess/config.sub 补丁 (0001, 0002)
3. 修复 configure 脚本 umask 077 → umask 022
4. `./configure --prefix=$DEFAULT_PREFIX`
5. `make -j2`
6. `make install DESTDIR=$TEST_PREFIX`
7. `make check` — 81/81 测试通过

## 上游测试结果
| 测试套件 | 总数 | 通过 | 跳过 | 失败 |
|----------|------|------|------|------|
| GD 2.3.3 | 81 | 81 | 0 | 0 |

## Conan 验证结果
| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ PASS | 预构建风险评估通过 |
| G1 | ✅ PASS | 配方完整性检查通过 |
| G2 | ✅ PASS | conan create 干净构建通过 |
| G3 | ✅ PASS | 系统同名库隔离验证通过 |
| G4 | ✅ PASS | 产物完整性检查通过 |
| L2 | ✅ PASS | 平台功能矩阵测试通过 |
| L4 | ✅ PASS | 静态安全扫描通过 |
| L5 | ✅ PASS | 产物基线对比通过 |

## 产物文件
- libgd.so.3.0.11 (共享库, 740KB)
- libgd.a (静态库, 1.1MB)
- 头文件: gd.h, gdcache.h, gdfontg.h 等 12 个
- pkg-config: gdlib.pc
- 工具: bdftogd, gd2copypal, gd2togif, gdcmpgif, giftogd2

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 HarmonyOS | 旧版 config.guess/sub (2018) 不支持 OHOS | 应用 0001/0002 补丁替换为 2022 版本 |
| 2 | configure 中 umask 077 导致临时目录创建失败 | E011: HMDFS umask 问题 | sed 替换 umask 077 → umask 022 |
| 3 | GitHub 源码下载超时 | 网络环境限制 | 使用 ghfast.top 镜像代理下载 |
| 4 | zlib 版本冲突 | libpng/1.6.58 要求 zlib/1.3.1.1 而非 zlib/1.3.1 | 修改 conanfile.py 使用 zlib/1.3.1.1 |
| 5 | CMake target 名称不匹配 | CMakeLists.txt 使用 GD::gd 但 Conan 生成 gd::gd | 修改 CMakeLists.txt 使用 gd::gd |
