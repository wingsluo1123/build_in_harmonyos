# 上游改写 CMakeDeps imported target 的 INTERFACE_LINK_LIBRARIES，链接丢失整个依赖库

Status: DRAFT
Source: sortmerna 4.3.7（分支 feat/sortmerna-4.3.7，2026-10-15）

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E447 | SDL2 系 vendored Find 模块在 CMakeDeps 下丢传递依赖/丢 include，方案是 conanfile 侧缓存变量桥接 | E447 的依赖发现走的是**变量式** vendored Find 模块；本条是 find_package CONFIG 正常命中 CMakeDeps、但上游随后用 `set_target_properties` **改写 imported target 属性**，把 CMakeDeps 编码在 INTERFACE_LINK_LIBRARIES 里的**库文件路径本身**抹掉——报错面与根因都不同 |
| E473 | 用 cmake_build_modules 注入 imported target（libwebp） | E473 是“缺 target 就补”；本条是“target 存在但被上游改写坏”，方向相反 |

检索关键词：`INTERFACE_LINK_LIBRARIES`、`set_target_properties`、`CMakeDeps`、`undefined symbol: rocksdb::`。
结论：既有条目均未覆盖“上游主动改写 CMakeDeps imported target 链接接口”这一模式 → 判定为增量。

## Scope（何时使用）

- CMake 项目，依赖经 Conan 2 CMakeDeps 以 CONFIG 模式提供（生成的 `*Config.cmake`）；
- 上游 `CMakeLists.txt` 中存在 `set_target_properties(<Dep>::<dep> PROPERTIES INTERFACE_LINK_LIBRARIES "...")`；
- 链接期报**该依赖库自身符号**全部 undefined（`referenced by` 全部指向本包对象文件）。

预扫描判定命令：

```bash
grep -Rn "set_target_properties" --include=CMakeLists.txt --include=*.cmake . | grep INTERFACE_LINK_LIBRARIES
```

## Symptom（真实日志，sortmerna 4.3.7 无补丁构建，OHOS aarch64 / clang 15 / Conan 2.29.1）

```
ld.lld: error: undefined symbol: rocksdb::DB::Open(rocksdb::Options const&, ...)
>>> referenced by kvdb.cpp
>>>               CMakeFiles/smr_objs.dir/kvdb.cpp.obj:(KeyValueDatabase::KeyValueDatabase(...))
ld.lld: error: undefined symbol: rocksdb::ReadOptions::ReadOptions()
>>> referenced by kvdb.cpp
...
clang++: error: linker command failed with exit code 1
```

注意报错面极具误导性：看起来像是“rocksdb7 包没编出来/没发布”，实际包完好，是链接行里根本没有 librocksdb.a。

## Root Cause

Conan 2 CMakeDeps 生成 imported target 时，把**库文件路径本身**与传递依赖一起编码进
`INTERFACE_LINK_LIBRARIES`（`$<$<CONFIG:Release>:...>` 生成表达式形式）。sortmerna 上游在
`src/sortmerna/CMakeLists.txt` 里有这么一段（动机是修正其自带 RocksDBTargets.cmake 写死的
libz 传递依赖）：

```cmake
if(NOT WIN32)
    if(ZLIB_LIBRARY_RELEASE)
        set_target_properties(RocksDB::rocksdb PROPERTIES
            INTERFACE_LINK_LIBRARIES "${ZLIB_LIBRARY_RELEASE};Threads::Threads"
        )
    endif()
endif()
```

这段代码针对的是“上游 setup.py 自建的 RocksDB”（其 config 文件确有该缺陷），但在 Conan
消费场景下它把 CMakeDeps 写入的库路径一并覆盖——`librocksdb.a` 整体不再参与链接，
于是 rocksdb 符号全部 undefined（若覆盖行保留了库路径，则退化为丢失
snappy/lz4/zstd/bzip2/gflags 传递依赖）。与平台无关，Linux/macOS/OHOS 同样命中。

## Workaround / 修复

最小补丁删除该改写块（本仓 `archives/s/sortmerna/4.3.7/patches/0001-keep-rocksdb-transitive-deps.patch`），
让 CMakeDeps 生成的完整链接接口生效。修复前后对照：

- 修复前：上述 ld.lld undefined symbol，链接失败；
- 修复后：`conan create archives/s/sortmerna/4.3.7 -pr:h=ohos-local -pr:b=ohos-local --build=missing` 全绿
  （G2 PASS，产物 `bin/sortmerna` 为 aarch64 musl ELF）。

若上游本意是裁剪传递依赖，正确做法是在消费方 conanfile 用 CMakeDeps 属性或上游自有选项表达，
不要改写 target 属性。

## Prevention（禁止做法）

1. 消费 Conan 2 CMakeDeps 包时保留上游对 imported target `INTERFACE_LINK_LIBRARIES` 的
   `set_target_properties` 改写——改写等于摘除整个库。
2. 往改写行里手工补回库路径（如 `"${ROCKSDB_LIBRARY};${ZLIB_LIBRARY_RELEASE};Threads::Threads"`）——
   与 CMakeDeps 依赖契约重复维护，依赖包增减传递依赖时静默腐烂。

## References

- 触发实例：archives/s/sortmerna/4.3.7（conanfile.py / patches/0001 / notes.md 问题表 #1）
- 相近条目：E447（vendored Find 模块丢传递依赖）、E473（cmake_build_modules 注入 imported target）
