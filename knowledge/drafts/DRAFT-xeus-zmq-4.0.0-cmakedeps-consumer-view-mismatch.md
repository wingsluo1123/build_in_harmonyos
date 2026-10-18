# DRAFT-xeus-zmq-4.0.0-cmakedeps-consumer-view-mismatch — Conan 2 库消费链上 CMakeDeps 生成视图与上游 CMakeLists 期望不匹配，conan create 主包 configure 阶段逐层失败

> **Contributor**: gcw_6YxinkyD | **Status**: DRAFT | **Updated**: 2026-10-15
> **Severity**: blocking (2) | **Category**: conan / cmake / packaging / c++-libraries
> **Audience**: 用 Conan 2 打包"消费多个已发布 Conan 库"的 C/C++ 库配方作者（尤其上游 CMakeLists 直接链接无命名空间 target、依赖 header-only 包装库、依赖无 CMake config 的库时）

## 触发（trigger）

xeus-zmq/4.0.0 OHOS PC aarch64 适配：主配方 requires `xeus/6.0.5`、
`cppzmq/4.10.0`、`zeromq/4.3.5`、`openssl/3.0.16`、`nlohmann_json/3.12.0`。
上游 CMakeLists 用 `find_package(xeus 5.0.0 REQUIRED)` + 链接无命名空间
`xeus`、`cppzmq` 目标 + `OpenSSL::Crypto`。conan create 主包 configure
阶段连续失败 4 次，每层原因独立且通用。

## 症状（symptom）

1. **版本范围语法被拒**：`self.requires("xeus/[>=6.0,<7.0]")` →
   `ERROR: "<7.0" in version range ">=6.0,<7.0" is not a valid option`
   （Conan 2.31；本项目 Conan 构建版本解析不接受逗号分隔区间）。
2. **依赖 config 未生成**：`generators` 目录只有 OpenSSLConfig.shim，
   `find_package(xeus)` 报
   `By not providing "Findxeus.cmake"... Could not find xeusConfig.cmake /
   xeus-config.cmake`——主配方未声明 `generators = "CMakeDeps"`，
   CMakeDeps 根本没运行。
3. **版本兼容被拒**：补上 CMakeDeps 后，
   `find_package(xeus 5.0.0 REQUIRED)` 拒绝
   `xeus-config.cmake, version: 6.0.5`——CMakeDeps 生成的
   `xeus-config-version.cmake` 强制 **major 版本相等**才
   `PACKAGE_VERSION_COMPATIBLE TRUE`（6 vs 5 直接 FALSE）。
4. **链接接口引用未加载 target**：自写 OpenSSLConfig.cmake shim 里
   `set_target_properties(OpenSSL::Crypto ... INTERFACE_LINK_LIBRARIES
   openssl::openssl)` 报
   `The link interface of target "OpenSSL::Crypto" contains: openssl::openssl
   but the target was not found`——shim 引用了 CMakeDeps 生成的
   `openssl::openssl`，但生成阶段没先加载 openssl-config.cmake。

## 机制（root cause）

CMakeDeps 在**消费端**生成一套与上游 CMakeLists 假设不同的 CMake 视图：

1. **ConfigVersion 强制 major 对齐**：CMakeDeps 生成的
   `*-config-version.cmake` 逻辑是
   `if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION) FALSE;
   else() major 相等才 TRUE; endif()`。上游 CMakeLists 里
   `find_package(xeus 5.0.0)` 是 **5.0.0 时代残留的最低版本声明**（该库实际
   配套 xeus 6.x，见 environment-dev.yml `xeus>=6,<7`），major 不同即被拒，
   即使 6.0.5 数值上满足 `>=5.0.0`。Conan 语义与 CMake
   `AnyNewerVersion` 语义不同：Conan 侧版本由 Conan 范围解析，CMake 侧
   major 必须完全对齐。
2. **目标命名空间**：CMakeDeps 生成 `xeus::xeus`、`libzmq::libzmq` 等
   命名空间 IMPORTED target；上游 CMakeLists 链接无命名空间 `xeus`
   （`target_link_libraries(... PUBLIC ${XEUS_TARGET_NAME})` 默认 `xeus`），
   不桥接直接报 `target "xeus" not found`。
3. **header-only 包装库不传播底层库**：cppzmq 是 header-only（Conan
   package 只有头），它的 cpp_info 不声明 libzmq；即便 cppzmq 配方
   `requires(zeromq)`，CMakeDeps 消费端 `cppzmq` target 的
   INTERFACE_LINK_LIBRARIES 不含 `libzmq::libzmq`。私实现链接
   `${CPPZMQ_TARGET_NAME}` 编译过但**链接期缺 libzmq 符号**，必须显式
   再链接 libzmq。
4. **无 CMake config 的库需 shim 且必须转发**：openssl 配方（手写
   Configure 构建）不导出任何 CMake config；消费端要么没有
   `OpenSSL::Crypto`，要么自己写 shim——shim 若引用 CMakeDeps target
   必须先 include 对应 config，否则生成阶段 target 不存在。
5. **签名工具路径**：OHOS 库产物需 llvm-objcopy 去 .codesign +
   binary-sign-tool 自签名，两工具在真机不同目录
   （`/data/service/hnp/bin` 与 `/storage/Users/currentUser/usr/local/bin`），
   写死单路径在裸 SSH 环境找不到。

## 修复（resolution）

xeus-zmq 4.0.0 配方（已真机验证通过）：

```python
# conanfile.py（要点）
generators = "CMakeDeps"                      # 类属性，缺它依赖 config 不生成
self.requires("xeus/[>=6.0 <7.0]", ...)       # 版本范围用空格分隔（Conan 2.31）
```

`patches/0001-CMakeLists.patch`（上游 CMakeLists 对接）：

```cmake
set(xeus_REQUIRED_VERSION 6.0.0)              # 5.0.0 → 6.0.0，major 对齐 CMakeDeps
if(TARGET xeus::xeus AND NOT TARGET xeus)     # 命名空间 → 无命名空间 alias
    add_library(xeus INTERFACE IMPORTED)
    set_property(TARGET xeus PROPERTY INTERFACE_LINK_LIBRARIES xeus::xeus)
endif()
if(NOT TARGET libzmq AND TARGET libzmq::libzmq)  # header-only 不传播 → 显式链接
    add_library(libzmq INTERFACE IMPORTED)
    set_property(TARGET libzmq PROPERTY INTERFACE_LINK_LIBRARIES libzmq::libzmq)
endif()
# macro(xeus_zmq_create_target): PRIVATE ${CPPZMQ_TARGET_NAME} libzmq
```

OpenSSLConfig.cmake shim（生成阶段，转发而非自造属性）：

```cmake
include("${CMAKE_CURRENT_LIST_DIR}/openssl-config.cmake")  # 先加载 CMakeDeps target
if(NOT TARGET OpenSSL::Crypto AND TARGET openssl::openssl)
    add_library(OpenSSL::Crypto INTERFACE IMPORTED)
    set_target_properties(OpenSSL::Crypto PROPERTIES
        INTERFACE_LINK_LIBRARIES openssl::openssl)
endif()
```

签名工具（build/package 阶段）：

```python
objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
signer  = shutil.which("binary-sign-tool") or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
```

验证（真机 frp-tip.com:56267，OHOS 6.0 aarch64，conan create 全流程）：
`conan create archives/x/xeus-zmq/4.0.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64
--build=missing -c tools.build:jobs=2` → configure/编译/安装/签名/package
全通过；test_package `./test_xeus_zmq` 输出 `xeus-zmq test passed`。

## 反模式（anti-patterns）

- ❌ 版本范围逗号写法 `[>=6.0,<7.0]`——本项目 Conan 构建报 invalid
  option；用空格 `[>=6.0 <7.0]`。
- ❌ 只补 patch 不补 `generators = "CMakeDeps"`——依赖 config 全部不生成，
  错误表现为"找不到 xeus"且诊断方向会误导到 find_package 路径。
- ❌ 把 `find_package(xeus 5.0.0)` 改成无版本参数或降低要求——正确方向是
  **对齐实际配套的 major**（提升到 6.0.0），既满足 CMakeDeps 的 major 校验，
  也反映真实依赖（xeus 6.x API）。
- ❌ OpenSSL shim 里硬编码 include 路径或引用未加载的 `openssl::openssl`
  ——路径会随 package 目录漂移；target 必须先 include CMakeDeps config。
  （python `.format()` 生成模板时 `${{CMAKE_CURRENT_LIST_DIR}}` 需双花括号转义。）
- ❌ 签名工具写死单一目录——裸 SSH 环境 PATH 不含工具目录，
  `shutil.which + 真机 fallback` 双路径最稳。
- ❌ 真机构建不设 `TMPDIR`（/tmp 只读）或不限并行
  （`-c tools.build:jobs=2`）——Toybox sh heredoc 报
  `can't create temporary file ... Read-only file system`，高并行有
  OOM 关机风险。

## 关联

- similar_to: E216/E221/E283/E307（Conan 依赖传播/CMakeDeps 家族）；
  DRAFT-xeus-5.0-test-package-explicit-deps-target-compat（库被消费侧的
  目标名兼容，本文是消费别的库一侧）；DRAFT-conan2-cmakedeps-
  transitive-include-strip（传递 include 置空）；DRAFT-binary-sign-tool-
  buildenv-ldlibrarypath（签名工具运行环境）。
- 互补案例：DRAFT-conan-shared-pkgconfig-requires-drop
  （PkgConfigDeps 流同样存在"传递依赖属性向下游裁剪"）。
