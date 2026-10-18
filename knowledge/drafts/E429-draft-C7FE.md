# E429 — 上游 CMake 假定系统路径时的四类报错；CMAKE_SKIP_RPATH 会让 rpath 全失效

## 错误特征（同一根因的四种面貌）
```
1) CMake Error: The following required packages were not found:  libusb-1.0 / libzstd / tinyxml2
2) libuuu/buffer.cpp:44:10: fatal error: 'bzlib.h' file not found
3) libuuu/http.cpp:506:41: error: use of undeclared identifier 'base64_encode'
4) Error relocating .../uuu: _ZN8tinyxml211XMLDocument5ParseEPKcm: symbol not found
   （二进制里没有任何 RPATH → 加载器解析到别处同名 so）
再补一类环境限制：
5) libc++abi: terminating due to uncaught exception of type std::runtime_error: Call libusb_init failure
```

## 触发条件
- 构建系统: CMake（上游假定依赖在系统路径）
- 阶段: build（configure / 编译 / 链接 / 运行）

## 根因分析
1. **`pkg_check_modules(... REQUIRED ...)`**：conan 隔离环境没有系统 `.pc` → 需要 `PkgConfigDeps` 生成。
2. **`include_directories` 漏依赖**：上游没写 BZip2 的 include（普通 Linux 有 `/usr/include` 兜底）。
3. **守卫不对称**：`base64_encode` 的**定义在 `#ifdef UUUSSL` 里**，而**使用处（506 行）没有守卫**；
   conan 下 `find_package(OpenSSL)` 不命中 → `OPENSSL_FOUND` 假 → 上游不定义 `UUUSSL` → 必炸。
4. **`set(CMAKE_SKIP_RPATH ON)`**：它使 `CMAKE_BUILD_RPATH`/`CMAKE_INSTALL_RPATH` 失效（实测二进制无
   RPATH）→ 运行期按默认路径找库，解析到别处同名 so → 符号重定位失败。
5. **硬件依赖 vs 无硬件环境**：uuu 在**解析参数前**就 `libusb_init` → 没有 USB 子系统时连 `-h` 都 abort。

## 解决方案
```cmake
# ②③ 把依赖的 include 直接塞进去（不要指望上游的 if(OPENSSL_FOUND) 分支）
include_directories("<bzip2>/include" "<openssl>/include")
set(UUUSSL "-DUUUSSL")                      # 无条件定义（使用处没有守卫）

# ④ 绕过 CMAKE_SKIP_RPATH：直接用链接器参数
set(CMAKE_SKIP_RPATH OFF)
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,-rpath,<dep1>/lib -Wl,-rpath,<dep2>/lib")
```
```python
# ① conan 侧
CMakeDeps(self).generate()
PkgConfigDeps(self).generate()      # ← 生成 .pc，供 pkg_check_modules
CMakeToolchain(self).generate()
```
运行时测试再叠加 `LD_LIBRARY_PATH=<各依赖>/lib` 作为兜底。

### 禁止做法
- ❌ 只设 `CMAKE_BUILD_RPATH`/`CMAKE_INSTALL_RPATH` 而不检查 `CMAKE_SKIP_RPATH`
- ❌ 把"无硬件环境导致的 abort"当成适配失败（应如实记录、不计为通过，也不让 build 失败）
- ❌ 为了方便改上游源码逻辑（本例只注入路径，不改行为）

## 验证
```bash
grep -n 'pkg_check_modules\|find_package\|include_directories\|CMAKE_SKIP_RPATH' libuuu/CMakeLists.txt uuu/CMakeLists.txt
readelf -d <build>/uuu/uuu | grep -E 'NEEDED|RPATH|RUNPATH'   # 确认 rpath/needed
<build>/uuu/uuu -h ; echo "rc=$?"                              # 无 USB 环境会 rc=-6（abort）
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：平台清单版本 vs 真实上游版本 / 上游无测试时补测并摊开构成 /
  判依赖先扣仓库已有 / autotools 依赖 include 与 LIBS 顺序 / sdist 缺测试数据 / Conan 依赖遮蔽 等）
