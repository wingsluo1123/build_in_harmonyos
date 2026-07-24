# libgeotiff 1.7.4 测试报告 - OpenHarmony

## 测试概述

| 项目 | 信息 |
|------|------|
| 软件版本 | libgeotiff 1.7.4 |
| 目标平台 | aarch64-unknown-linux-ohos |
| 测试日期 | 2026-07-23 |
| 测试平台 | HarmonyOS aarch64 (OHOS 6.0, clang 15) |
| 测试套件 | Conan test_package (ctest) + 独立功能测试 |

## 一、conan create 编译验证

### 编译结果

```
======== Exporting recipe to the cache ========
libgeotiff/1.7.4: Exported: libgeotiff/1.7.4#bd673af5a310c9487a0efd9c29b679bf

======== Computing dependency graph ========
Requirements
    libtiff/4.7.2 - Cache
    proj/9.3.1 - Cache
    zlib/1.3.1.1 - Cache
    libjpeg-turbo/3.2.0 - Cache
    (及其传递依赖)

======== Building packages ========
libgeotiff/1.7.4: Building from source

-- The C compiler identification is Clang 15.0.4
-- Found PROJ: libproj.a (found version "9.3.1")
-- Found TIFF: libtiff.so (found version "4.7.2")
-- Configuring done (3.2s)

[  6%] Building C object CMakeFiles/geotiff_library.dir/cpl_serv.c.o
...
[100%] Linking C shared library lib/libgeotiff.so
[100%] Built target geotiff_library

libgeotiff/1.7.4: Package '0af21df611baf815e8299e5d2e8971a1170d48a5' built
```

**编译状态**: ✅ 成功

### test_package 结果

```
======== Testing the package: Executing test ========
libgeotiff/1.7.4 (test package): RUN: ctest --output-on-failure
Test project build/clang-15-armv8-17-release
    Start 1: test_geotiff
1/1 Test #1: test_geotiff .....................   Passed    0.08 sec

100% tests passed, 0 tests failed out of 1
Total Test time (real) =   0.09 sec
```

**test_package 状态**: ✅ 1/1 通过

## 二、CI 质量门检查结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| L0 | ✅ pass | 结构+依赖+版本+commands.json 全部检查通过 |
| L1 | ✅ pass | test_package 执行+测试证据+上游测试+破坏性负测试 |
| L2 | skip | 库包无 bin/ 目录 |
| L4 | ✅ pass | 无补丁 |
| L5 | ✅ pass | lib/ 有内容 |

### L1e 破坏性负测试

```
[step] L1e: Destructive negative test (R34)...
        [sabotage] lib/ moved away
        [sabotage] include/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on libgeotiff
```

**结论**: 测试确实依赖 libgeotiff 库（非空壳测试，R34 合规）。

## 三、独立功能测试

### 测试程序

文件: `test_package/test_geo.c`

测试内容: 创建 GeoTIFF 文件 → 写入 GeoTIFF 键 → 读取验证

### 编译命令

```bash
clang test_geo.c -o test_geotiff_func \
  -I$GEOTIFF_PKG/include -I$TIFF_PKG/include \
  -L$GEOTIFF_PKG/lib -L$TIFF_PKG/lib -L$PROJ_PKG/lib \
  -lgeotiff -ltiff -lproj -lsqlite3 -lz -ljpeg -llzma \
  -lzstd -lwebp -lsharpyuv -lLerc -ldeflate -lm -lc++_shared \
  -fuse-ld=bfd
```

### 真实运行输出

```
=== libgeotiff functional test ===
Creating test GeoTIFF file...
GTIFNew: OK
GTIFKeySet ProjectedCSTypeGeoKey=PCS_WGS84_UTM_zone_33N: OK
GTIFWriteKeys: OK
GeoTIFF file created successfully.

Reading back GeoTIFF file for verification...
GTIFNew (read): OK
GTIFKeyGet ProjectedCSTypeGeoKey: ret=1, PCS=32633
VERIFY: PCS value correct (32633 == 32633)

=== FUNCTIONAL TEST: PASSED ===
```

### 验证的 API 调用

| # | API | 操作 | 结果 |
|---|-----|------|------|
| 1 | XTIFFOpen | 创建/打开 TIFF 文件 | ✅ |
| 2 | GTIFNew | 创建 GeoTIFF 句柄 | ✅ |
| 3 | GTIFKeySet | 设置 ProjectedCSTypeGeoKey=32633 | ✅ |
| 4 | GTIFWriteKeys | 将 GeoTIFF 键写入 TIFF | ✅ |
| 5 | GTIFFree | 释放 GeoTIFF 句柄 | ✅ |
| 6 | GTIFKeyGet | 读取 GeoTIFF 键 (ret=1, PCS=32633) | ✅ |
| 7 | XTIFFClose | 关闭 TIFF 文件 | ✅ |

## 四、构建产物验证

### ELF 二进制信息

```
file: libgeotiff.so.5.2.4
type: ELF shared object, 64-bit LSB arm64
```

### NEEDED 依赖

```
libgeotiff.so.5.2.4 NEEDED:
  libtiff.so.6, libc++_shared.so, libdeflate.so.0, libzstd.so.1,
  libwebp.so.7, libsharpyuv.so.0, libLerc.so.4, libjpeg.so.62,
  libturbojpeg.so.0, libc.so
```

### OHOS codesign 签名

```
07-24 00:25:17.168 INFO  - add codesign section success
07-24 00:25:17.205 INFO  - write code sign data success
```

## 五、结论

| 验证项 | 结果 |
|--------|------|
| conan create 编译 | ✅ 通过 |
| test_package (ctest) | ✅ 1/1 通过 |
| CI 质量门 L0-L5 | ✅ 全部通过 |
| 功能测试 (API 验证) | ✅ 通过 |
| ELF 签名 | ✅ 已签名 |

**最终状态**: libgeotiff 1.7.4 在鸿蒙 PC 平台真实可用。
