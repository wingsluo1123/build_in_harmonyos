# 静态链接 libsodium 时上游动态库目标 ld.lld duplicate symbol: randombytes → 静态-only 关闭动态目标

- **草稿 ID**: DRAFT-libxeddsa-2.0.1-static-libsodium-randombytes-duplicate-dynamic-opt-out
- **来源**: libxeddsa 2.0.1 适配（conan create G2 首败：xeddsa_dynamic 链接失败）
- **分类**: linking / cmake / static-link / crypto / build-option
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 2（build 阶段链接失败，报错指向性强）

## 问题 / 错误签名

- conan create 构建日志：
  - `ld.lld: error: duplicate symbol: randombytes`
  - `>>> defined at fastrandombytes.c`（ref10/CMakeFiles/fastrandombytes_objects.dir/...）
  - `>>> defined at randombytes.c ... in archive .../libsodium.a`（libsodium_la-randombytes.o）
- 静态库 `xeddsa_static` 构建成功；仅动态库 `xeddsa_dynamic` 链接失败。

## 根因

libxeddsa 的 CMakeLists 在非 EMSCRIPTEN 分支**无条件**
`add_library(xeddsa_dynamic SHARED $<TARGET_OBJECTS:xeddsa_objects>)`，
其 PUBLIC 链接面包含 ref10 各 OBJECT 库与 `sodium`：

- ref10/fastrandombytes 自带实现 `randombytes()`（独立强符号）；
- ohpcd 发布的 libsodium 为**静态-only**（libsodium.a），同样导出
  `randombytes()`。

链接动态库时两个强符号同时可见 → duplicate symbol。归档文件（xeddsa_static）
不解析符号，所以静态库不受影响。

## 最小修复（真机验证）

上游补丁 `patches/0001-CMakeLists.txt.patch`：把三处动态目标包进受控开关

```cmake
if (NOT DEFINED EMSCRIPTEN AND XEDDSA_BUILD_DYNAMIC)
    add_library(xeddsa_dynamic SHARED ...)
    ...
    install(TARGETS xeddsa_dynamic)
endif ()

if (NOT DEFINED EMSCRIPTEN AND XEDDSA_BUILD_DYNAMIC)
    add_executable(xeddsa_test_dynamic ...)
endif ()

if (BUILD_TESTING)
    add_test(NAME xeddsa_test_static COMMAND xeddsa_test_static)
    if (NOT DEFINED EMSCRIPTEN AND XEDDSA_BUILD_DYNAMIC)
        add_test(NAME xeddsa_test_dynamic COMMAND xeddsa_test_dynamic)
    endif ()
endif ()
```

配方 generate()：

```python
tc.variables["XEDDSA_BUILD_DYNAMIC"] = "OFF"
```

验证：conan-verify 8 门禁全绿；test_package 消费者链接
libxeddsa.a + libsodium.a 无重复符号（final 可执行文件仅拉取被引用 OBJECT）。

## 影响面与推广

- 识别：`duplicate symbol: <符号>` + `defined at <上游自带实现>` +
  `in archive <依赖静态库>`，且上游一个 CMakeLists 同时建 static+dynamic。
- 典型场景：密码/加密库自带 ref10/ref 实现，依赖 libsodium/OpenSSL 静态库；
  OHOS 生态 libsodium 只发静态包，动态目标必踩。
- 若下游确需 .so：改用 `BUILD_SHARED_LIBS` 统一驱动 static/dynamic 二选一
  （E283/E288 系），本条记录"静态-only 时关闭动态目标"的最小干预。
- 与 E163（`__packed` OHOS 头文件全局符号）同属 duplicate symbol 面但根因
  不同（头文件全局变量 vs 静态依赖符号重叠）；与 jwt-cpp 草稿（错误注入
  自定义符号 + HUNTER 守卫）也不同（上游测试语义 vs 构建目标选择）。

## 反例 / 限制

- 不适用：上游正确使用 BUILD_SHARED_LIBS 控制的目标；依赖是共享库（符号
  由加载器解析，无重复定义问题）；两个符号仅存在于不同翻译单元且未被同一
  链接单元同时引用。
- 关闭动态目标会减少交付形态（无 .so），需在配方 options 语义中明确
  static-only（libsodium 发布形态约束下合理）。
