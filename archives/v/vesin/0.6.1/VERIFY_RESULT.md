# vesin 0.6.1 — Conan 本地编译+测试验证报告（重做）

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名 | vesin |
| 版本 | 0.6.1 |
| 构建系统 | cmake |
| 源码 URL | https://github.com/Luthaf/vesin/archive/refs/tags/v0.6.1.tar.gz |
| 源码 SHA256 | 2846f238c61109791e4315acc145c740d338f4f994bfd0e04ab2bfceb82077a0 |
| OHOS Profile | ci/conan/profiles/ohos-aarch64 |
| Conan 版本 | OHOS 适配版 2.29.1 |
| 编译器 | Clang 15.0.4 (OHOS NDK llvm/bin/clang++) |
| 目标平台 | OHOS 6.0 / armv8 (aarch64) |

## 编译状态

**成功 ✅ — 确认为本地源码编译（非远程下载）**

### 上次打回原因修复

上次 `conan create` 使用 `--build=vesin` 仍从远程 ohpcd 下载了预编译二进制包，日志中无 cmake configure / clang 编译过程。本次增加 `-nr`（不使用远程仓库）参数，强制完全本地构建：

```bash
conan create archives/v/vesin/0.6.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=vesin --build=missing -nr
```

### 远程下载排除验证

日志中 grep `Download (ohpcd)` / `Retrieving package.*from remote` / `Downloaded package` 结果为空（exit code 1），确认无远程二进制下载。

## 本地编译证据（日志行号 + 原文）

### 1. 源码下载（从 GitHub 官方源，非 conan 远程仓库）

- **行 78**: `vesin/0.6.1: Sources correctly downloaded from https://github.com/Luthaf/vesin/archive/refs/tags/v0.6.1.tar.gz`
- **行 80**: `vesin/0.6.1: Sources correctly downloaded from https://github.com/metatensor/gpu-lite/archive/6c221167aeca7e113ea6f27e9a2e12391bdb189a.tar.gz`

### 2. 从源码构建声明

- **行 83**: `vesin/0.6.1: Building from source`

### 3. CMake configure 过程

- **行 118**: `-- The C compiler identification is Clang 15.0.4`
- **行 119**: `-- The CXX compiler identification is Clang 15.0.4`
- **行 134**: `-- Check for working C compiler: /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang - skipped`
- **行 151**: `-- Check for working CXX compiler: /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++ - skipped`
- **行 198**: `-- Configuring done (5.4s)`
- **行 199**: `-- Generating done (0.0s)`

### 4. Clang 编译过程（Building CXX object）

- **行 213**: `[ 41%] Building CXX object vesin/CMakeFiles/vesin.dir/src/vesin.cpp.o`
- **行 215**: `[ 50%] Building CXX object vesin/CMakeFiles/vesin.dir/src/threadpool.cpp.o`
- **行 217**: `[ 58%] Building CXX object vesin/CMakeFiles/vesin.dir/src/cpu_cell_list.cpp.o`
- **行 219**: `[ 66%] Building CXX object vesin/CMakeFiles/vesin.dir/src/verlet.cpp.o`
- **行 221**: `[ 75%] Building CXX object vesin/CMakeFiles/vesin.dir/src/vesin_cuda.cpp.o`
- **行 223**: `[ 83%] Building CXX object vesin/CMakeFiles/vesin.dir/src/verlet_cuda.cpp.o`
- **行 225**: `[ 91%] Building CXX object vesin/CMakeFiles/vesin.dir/src/cuda_buffers.cpp.o`

### 5. libvesin.so 链接产出

- **行 227**: `[100%] Linking CXX shared library libvesin.so`
- **行 237**: `-- Installing: /storage/Users/currentUser/.conan2/p/b/vesinb2d9640964a04/p/lib/libvesin.so`

### 6. 代码签名（OHOS XPM 要求）

- **行 240**: `vesin/0.6.1: RUN: /data/service/hnp/bin/llvm-objcopy --remove-section .codesign ... libvesin.so`
- **行 242**: `vesin/0.6.1: RUN: /data/service/hnp/bin/binary-sign-tool sign -inFile ... libvesin.so -outFile ... libvesin.so -selfSign 1`
- **行 244**: `08-10 11:30:02.216 INFO  - add codesign section success`
- **行 245**: `08-10 11:30:02.224 INFO  - write code sign data success`

## conan create 结果

| 检查项 | 结果 |
|--------|------|
| 配方导出 | ✅ 成功 |
| 依赖图计算 | ✅ 成功（无外部依赖） |
| 二进制包构建（本地源码编译） | ✅ 成功 |
| test_package 编译 | ✅ 成功 |
| test_package 运行 | ✅ 成功 |

### Conan 缓存中的 ref

```
vesin/0.6.1#53d9d8cedbf0857e53fcad583ca8e84a
  package: 01d92cf349a0dd98ff915f4bd99a04430171517f#435717aa27abdab55703833c578cc560
```

`conan list vesin` 输出确认缓存已建立：

```
Local Cache
  vesin
    vesin/0.6.1
```

## test_package 执行结果

### 命令

```bash
conan test archives/v/vesin/0.6.1/test_package "vesin/0.6.1" \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 测试内容

test.cpp 对 vesin 近邻表计算进行真实几何验证：
- 构造 4 点正方形（边长 1.0），用 vesin_neighbors() 计算近邻对
- cutoff=1.5：4 条边 + 2 条对角线 = 6 对
- cutoff=1.2：4 条边（对角线 √2≈1.414 被排除）= 4 对
- 同时验证所有距离落在 (0, cutoff] 范围内

### 执行输出

```
[ok] cutoff=1.5 计算成功且所有距离都在 cutoff 内
[ok] cutoff=1.5 → 6 对（4 条边 + 2 条对角线）
[ok] cutoff=1.2 计算成功且所有距离都在 cutoff 内
[ok] cutoff=1.2 → 4 对（对角线 1.414 被排除，证明 cutoff 生效）

vesin 0.6.1: 全部断言通过
```

### 统计

| 指标 | 值 |
|------|-----|
| 断言通过数 | 4 |
| 断言失败数 | 0 |
| 通过率 | **100%（4/4）** |
| 退出码 | 0 |

## 结论

| 项目 | 结果 |
|------|------|
| 编译状态 | ✅ 成功 |
| 是否为本地编译（非远程下载） | ✅ 是 — 日志含完整 cmake configure + clang 编译 + libvesin.so 链接 |
| conan create | ✅ 成功 |
| conan test (test_package) | ✅ 成功 |
| 测试通过率 | **100%（4/4 断言通过）** |
| 是否需要打回重做 | **否** |

## 完整日志路径

```
/storage/Users/currentUser/Desktop/build_in_harmonyos/.vesin-verify.log
```

日志包含三段完整输出（共 367 行）：
1. `conan create ... -nr`（强制本地构建 + test_package 自动执行）— 行 1~289
2. `conan test ...`（独立 test_package 验证）— 行 290~361
3. `conan list vesin`（缓存确认）— 行 363~367
