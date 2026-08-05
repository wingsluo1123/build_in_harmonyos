# libid3tag 0.16.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: published

## 手动编译步骤（非 Conan）

1. **init-build**: 使用 --no-download 手动下载 tarball（Debian pool mirror，Savannah SSL/超时不可用）
2. **CMake configure**:
   ```bash
   mkdir -p build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DBUILD_SHARED_LIBS=ON \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         ..
   ```
3. **Build**: `make -j1` — 成功，仅有指针类型警告（char/unsigned char 混用）
4. **Install (DESTDIR)**: `make install DESTDIR=$TEST_PREFIX` — 安装 libid3tag.so, id3tag.h, id3tag.pc, cmake configs
5. **Tests**: `ctest` — 无测试套件；编写 C 测试程序进行真实验证（9 项测试、67 断言，全部 PASS），详见 `reports/test-report.md`
6. **Verify**: G1-G4 全部 PASS
7. **Package**: libid3tag-0.16.3-ohos-aarch64.tar.gz (258KB)
8. **Local install**: `make install` — 安装到 ~/usr/local
9. **Finish**: published

## Conan 适配步骤

### 概述
将 libid3tag 0.16.3 适配为 Conan 2.x 包，使用 ohpcd 远端的 zlib/1.3.1 作为依赖。

### 创建文件
- `conanfile.py` — Conan 2.x 配方（CMake 构建系统，zlib/1.3.1 依赖）
- `conandata.yml` — 源码 URL 和 sha256
- `test_package/conanfile.py` — 测试包配方
- `test_package/CMakeLists.txt` — 测试 CMake 配置
- `test_package/test_package.c` — 测试 C 源码（调用 id3 API）

### 构建命令
```bash
# 首次构建（需重编译 zlib 带 -fPIC）
CFLAGS="-fPIC" conan create archives/l/libid3tag/0.16.3/conanfile.py \
    -pr:h=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
    -pr:b=default --build="*"

# 后续构建（zlib 已在 cache 中带 -fPIC）
conan create archives/l/libid3tag/0.16.3/conanfile.py \
    -pr:h=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
    -pr:b=default --build=missing
```

### 构建中遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Package type is 'library', but no 'shared' option declared` | Conan 2 要求 library 类型必须声明 shared 选项 | 添加 `options` 和 `default_options` 声明 shared/fPIC |
| 2 | `cmake_minimum_required(VERSION 3.1.0)` 失败 | CMake 4.x 不兼容 < 3.5 的最低版本要求；toolchain 中的 cache variable 在 project() 之后加载，早于 cmake_minimum_required() | 在 build() 中直接修改 CMakeLists.txt，将 3.1.0 提升为 3.5 |
| 3 | `Target "id3tag" links to ZLIB::ZLIB but target was not found` | CMakeDeps 生成 lowercase `zlib::zlib`，但源码用 `ZLIB::ZLIB` | 在 build() 中替换 `ZLIB::ZLIB` 为 `zlib::zlib` |
| 4 | `relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol z_errmsg; recompile with -fPIC` | ohpcd 远端 zlib 配方为静态专用（无 fPIC 选项），libz.a 未用 -fPIC 编译，无法链接进 libid3tag.so | 使用 `CFLAGS=-fPIC` 环境变量 + `--build="*"` 强制重编译 zlib |

### 测试结果
```
libid3tag version: ID3 Tag Library 0.16.3
Created new ID3 tag (version 0x0400)
Attached TIT2 frame with title "Test Title"
Render query size: 47 bytes
Rendered tag: 47 bytes
Parsed tag version: 0x0400
Found TIT2 frame in parsed tag
Genre[0]: Blues

All tests PASSED
```

测试覆盖:
- 库版本号验证 ✅
- ID3 标签创建 ✅
- 帧创建与附加（TIT2 title frame） ✅
- 标签渲染（id3_tag_render） ✅
- 标签解析（id3_tag_parse） ✅
- 帧查找（id3_tag_findframe） ✅
- 流派数据库查询（id3_genre_index） ✅

### Conan 包信息
- 包引用: `libid3tag/0.16.3#7ac35bd0c68fe214787bae90fd35ca82`
- 包 ID: `2bbe66435e0156d95911d24ac24af55e674c4c5e`
- 包修订: `de939c2307efcd3aba21fd154b1b3f2b`
- 配置: `os=OHOS arch=armv8 compiler=clang compiler.version=15 build_type=Release shared=True`
- 包内容: `lib/libid3tag.so`, `include/id3tag.h`, `lib/pkgconfig/id3tag.pc`, `lib/cmake/id3tag/*`

### 源码修改

无补丁文件。在 build() 方法中通过字符串替换修改 CMakeLists.txt:
1. `cmake_minimum_required(VERSION 3.1.0)` → `cmake_minimum_required(VERSION 3.5)` — CMake 4.x 兼容性
2. `ZLIB::ZLIB` → `zlib::zlib` — 对齐 Conan CMakeDeps 生成的目标名

## 遇到的问题与解决方案（手动编译）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 下载超时/404 | Savannah 镜像在当前环境不可达 | 使用 Debian pool mirror: ftp.debian.org |
| 2 | SSL 证书验证失败 | 系统缺少 CA 证书 | 使用 install-ca-certs.py + SSL_CERT_FILE 环境变量 |
| 3 | CMake 兼容性错误 | cmake_minimum_required(3.1) 与 CMake 4.x 不兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | init-build 误判为 autotools | 项目只有 CMakeLists.txt，无 configure | 手动更新 manifest.yaml build_system=cmake |
| 5 | G0 clean-verify 失败 | clean-verify 只支持 autotools ./configure | 创建 hints/configure.sh cmake wrapper；G0 已手动验证通过 |

## 依赖版本

- zlib/1.3.1（通过 Conan ohpcd 远端管理，静态库带 -fPIC）

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion id3tag  → 0.16.3
pkg-config --libs id3tag        → -L/storage/Users/currentUser/usr/local/lib -lid3tag -lz
pkg-config --cflags id3tag      → -I/storage/Users/currentUser/usr/local/include

# 文件验证
ls ~/usr/local/lib/libid3tag*   → libid3tag.so (182656 bytes)
ls ~/usr/local/include/id3tag.h → id3tag.h (10650 bytes)
ls ~/usr/local/lib/pkgconfig/id3tag.pc → id3tag.pc
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libid3tag-0.16.3-ohos-aarch64.tar.gz | 258KB | 预编译包（含 .so, .h, .pc, cmake configs） |
| libid3tag-0.16.3-ohos-aarch64-debug.tar.gz | 45KB | debug 符号包 |

## 注意事项

- libid3tag 0.16.3 使用 CMake 构建系统，不是 autotools
- G0 clean-verify 需要 hints/configure.sh wrapper 支持 CMake
- 编译产物只有 .so（共享库），无 .a（静态库）
- 原始下载 URL Savannah 不可用，需用 Debian mirror 替代
- CMake 需要添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 才能兼容
- Conan 适配: zlib 静态库需 CFLAGS=-fPIC 重编译以链接进 .so
- Conan 适配: CMakeDeps 生成 lowercase 目标名，需对齐源码

---

**编译结束**: 2026-05-21 16:56（手动）
**Conan 适配**: 2026-08-05
**最终状态**: published
