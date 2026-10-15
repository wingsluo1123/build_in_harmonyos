# E550 — Conan 配方 `generate()` 漏调 `CMakeDeps` ⇒ `find_package` 退回 Find 模块，静默链上宿主同名共享库

- 状态：草稿（待知识库主编审核，拟提升编号 E550）
- 关联 PR：feat/vector-blf-2.4.2（vector-blf 2.4.2 适配）
- 关联规则：R26（系统同名库必须静态）

## 错误特征

构建**成功**、`conan create` **通过**，但产物里悄悄多了一条指向宿主库的依赖：

```
$ readelf -d <pkg>/lib/libX.so | grep NEEDED
  (NEEDED)  Shared library: [libz.so.1]      # ← 本应不存在（zlib 应静态内嵌）
```

或反向特征——同名库符号没有静态内嵌进来：

```
$ llvm-nm -D <pkg>/lib/libX.so | grep -c uncompress
0                                            # 符号不在本库内
```

`conan create` 日志里**看不到任何错误**；异常只在换机器/CI 干净环境时爆出：

```
./test_x: error while loading shared libraries: libz.so.1: cannot open shared object file
```

## 触发条件

- 构建系统：CMake（上游用 `find_package(<Pkg>)`，尤其是消费 `${<PKG>_LIBRARIES}` 这类旧式变量的项目）
- 阶段：configuration（配置期找到了错误的包）+ linking（链上了宿主库）
- 配方形态：`conanfile.py` 里写了 `def generate(self)` 但**只调用了 `CMakeToolchain(self).generate()`**
- 环境特征：构建机上恰好装了同名库（zlib / sqlite3 / libpng / openssl / libxml2 …），
  且它在 CMake 默认搜索路径里（本机实测：`~/.harmonybrew/lib/libz.so.1.3.1.zlib-ng`）

## 根因分析

1. Conan 2 的 `CMakeDeps` **不是自动生成**的：配方必须显式
   `CMakeDeps(self).generate()`（或用 `generators = "CMakeDeps"`），否则 build 目录里
   不会出现 `<Pkg>Config.cmake` / `<Pkg>Targets.cmake`。
2. `CMakeToolchain` 生成的 `conan_toolchain.cmake`，在
   `conan_cmakedeps_paths.cmake` 不存在时走 `else()` 分支（会设
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`，并把 generators 目录 prepend 到
   `CMAKE_PREFIX_PATH`）——但 generators 目录里此时**没有任何 `<Pkg>Config.cmake`**，
   config 模式无包可找，`find_package` 回落到 CMake 内置 `Find<Pkg>` **模块模式**。
3. 内置 `FindZLIB` 等模块会去系统路径 `find_path`/`find_library`，命中构建机上的
   同名库（可能是**共享库**，甚至可能是另一种实现，如 zlib-ng）→ 链接期写入
   `NEEDED libz.so.1`。
4. 双重危害：①违反 R26（系统同名库必须静态）；②包隐式依赖构建机路径，
   CI/他机运行期缺库或链接到不同实现的库，压缩等行为可能不兼容。

**为什么手工编译时不复现**：手工验证时往往用命令行
`conan install --requires=zlib/... -g CMakeDeps -g CMakeToolchain`，`CMakeDeps` 是
显式指定的 → 有 `ZLIBConfig.cmake` → config 模式命中 → 静态 `libz.a`。
只有 `conan create`（用配方自己的 `generate()`）才暴露该缺陷。

## 解决方案

### 推荐方案

在 `generate()` 里显式生成 `CMakeDeps`：

```python
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()
```

若上游一定要走内置 Find 模块（例如自带 `FindXXX.cmake`），退一步用缓存变量兜底：

```python
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
```

### 禁止做法

- ❌ 只看 `conan create` 退出码 0 就认为依赖链正确 —— 该缺陷**不报错**。
- ❌ 用"宿主库能跑通"解释 `NEEDED libz.so.1` —— 换机器即失效，且违反 R26。
- ❌ 把 `requires()` 删掉来"消除"症状 —— 依赖是真实构建依赖，删掉后配置期直接失败。

## 验证

```bash
# 1) 产物不得出现宿主同名库
readelf -d <pkg>/lib/*.so | grep NEEDED
#    期望: 只有 libc++_shared.so / libc.so（无 libz.so.1 等）

# 2) 同名库符号应静态内嵌在本库内
llvm-nm <pkg>/lib/*.so | grep -E " T .*(uncompress|compress2|crc32)$"

# 3) CMakeDeps 确实生成了 config 文件
ls <build-folder>/generators/*Config.cmake

# 4) 干净环境复验（CI 同口径）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
              --build=missing --user=ohpcd --channel=stable
```

## 关联条目

- E092 — CMake 在 OHOS 上把系统名识别为 HarmonyOS（同一次适配中命中的平台类条目）
- E216 / E447 / E473 — CMakeDeps 生成文件与上游 Find 模块/旧式变量之间的桥接类问题
