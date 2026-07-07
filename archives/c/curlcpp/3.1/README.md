# curlcpp 3.1 — OpenHarmony 编译归档

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | curlcpp |
| 版本 | 3.1 |
| 描述 | Object oriented C++ wrapper for CURL (libcurl) |
| 许可证 | MIT |
| 构建系统 | CMake |
| 源码 URL | https://github.com/JosephP91/curlcpp/archive/refs/tags/3.1.tar.gz |
| SHA256 | ba7aeed9fde9e5081936fbe08f7a584e452f9ac1199e5fabffbb3cfc95e85f4b |
| 编译状态 | **published** |
| 编译日期 | 2026-07-02 |
| Conan 引用 | `curlcpp/3.1@ohpcd/stable` |
| Conan 包 ID | `9c32778feeb9d7a7ee6e1c459e26884f35c79855` |

## 编译环境

- 操作系统: HarmonyOS HongMeng Kernel 1.11.0 aarch64
- 编译器: Clang 15.0.4 (libc++)
- CMake: 4.1.2
- Conan: 2.12.0

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| libcurl | 8.19.0 | 系统安装 (~/usr/local) |
| OpenSSL | 系统版本 | 系统安装 (~/usr/local) |
| zlib | 系统版本 | 系统安装 (~/usr/local) |

> **注意**: Conan 远程仓库 (ohpcd) 暂无 curl/openssl 包。conanfile.py 通过 `CMAKE_PREFIX_PATH` 指向系统 libcurl 作为回退。待 `curl/8.15.0@ohpcd/stable` 发布后，取消 conanfile.py 中 `requirements()` 的注释即可。

## 编译配置

```bash
cmake .. \
    -DBUILD_SHARED_LIBS=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCURLCPP_USE_PKGCONFIG=OFF
```

- `BUILD_SHARED_LIBS=OFF`: 静态链接 (R26)
- `CMAKE_BUILD_TYPE=Release`: 发布构建

## 补丁

### 0001-include-curl_easy.h.patch

**类型**: portability
**文件**: `include/curl_easy.h`
**问题**: `CURLOPT_OBSOLETE72` 在新版 libcurl 中定义为纯 int (9999)，不能用作 C++ 模板参数 `CURLoption`。
**修复**: 注释掉 `CURLCPP_DEFINE_OPTION(CURLOPT_OBSOLETE72, long)` 行（该选项已标记 OBSOLETE）。

## 产物

| 产物 | 说明 |
|------|------|
| `lib/libcurlcpp.a` | 静态库 (355,104 bytes) |
| `include/curlcpp/*.h` | 22 个头文件 |
| `lib/cmake/curlcpp-config.cmake` | CMake 集成文件 |
| `lib/pkgconfig/curlcpp.pc` | pkg-config 文件 |

## 验证结果

### Conan 配方验证 (8 道门禁)

| 门禁 | 结果 |
|------|------|
| G0: 预构建风险评估 | ✅ PASS |
| G1: 配方完整性 | ✅ PASS |
| G2: conan create | ✅ PASS |
| G3: 静态链接 R26 | ✅ PASS |
| G4: 产物完整性 | ✅ PASS |
| L2: 平台功能矩阵 | ✅ PASS |
| L4: 安全扫描 | ✅ PASS |
| L5: 基线对比 | ✅ PASS |

### 端到端功能测试

使用 curlcpp API 发起 HTTP GET 请求到 httpbin.org，收到 HTTP 200 响应，220 字节 JSON 数据。

详见 `reports/test-report.md` 和 `tests/` 目录。

## 目录结构

```
archives/c/curlcpp/3.1/
├── manifest.yaml          # 归档清单
├── conanfile.py           # Conan 配方
├── conandata.yml          # Conan 数据 (源码URL + SHA256 + 补丁)
├── notes.md               # 适配笔记
├── README.md              # 本文件
├── patches/
│   └── 0001-include-curl_easy.h.patch
├── test_package/          # Conan test_package
│   ├── conanfile.py
│   ├── CMakeLists.txt
│   └── test.cpp
├── tests/                 # 端到端功能测试
│   ├── curlcpp_func_test.cpp
│   ├── func-test-output.txt
│   └── build-cmd.txt
└── reports/
    ├── conan-verify-report.md
    ├── conan-create.log
    ├── test-report.md
    └── baseline.json
```
