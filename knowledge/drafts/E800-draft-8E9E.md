# E800 — CMake 到第一个 project() 才加载 toolchain：project() 之前读的变量必须走 cli_args

## 错误特征

```
CMake Error at CMakeLists.txt:32 (project):
  VERSION "HEAD-HASH-NOTFOUND.HEAD-HASH-NOTFOUND.HEAD-HASH-NOTFOUND" format invalid.
```
或：
```
CMake Error at src/CMakeLists.txt:4 (include):
  include could not find requested file: Versioning
```
配方里 `tc.variables["ADS_VERSION"]` 明明已写入 `conan_toolchain.cmake`，configure
阶段却看不到该变量。

## 触发条件

- 构建系统: cmake（Conan 配方 + CMakeToolchain）
- 阶段: configure（第一个 `project()` 前后）
- 上游特征: 在 `project()` **之前**读取版本/路径/选项变量（典型：`if(NOT ADS_VERSION)`
  决定版本来源，或在分支里 `set(CMAKE_MODULE_PATH ...)`）

## 根因分析

CMake 在**第一个 `project()` 命令处**才包含 `CMAKE_TOOLCHAIN_FILE`。Conan 的
`CMakeToolchain` 把 `tc.variables` / `tc.cache_variables` 全部写进
`conan_toolchain.cmake`，因此这些变量在 `project()` 之前的 CMakeLists.txt 语句里
**不可见**。上游 `if(NOT ADS_VERSION)` 于是走了 git 分支，release tarball 无 `.git`
→ `git describe` 返回 `HEAD-HASH-NOTFOUND` → `project(... VERSION
HEAD-HASH-NOTFOUND.… )` 直接 FATAL。

同一机制的第二处后果：上游只在 `if(NOT ADS_VERSION)` 分支里
`set(CMAKE_MODULE_PATH <src>/cmake/modules)`，而 `src/CMakeLists.txt` 无条件
`include(Versioning)`，因此外部传 `ADS_VERSION` 时模块路径会丢失。

## 解决方案

### 推荐方案

把"必须在 `project()` 之前生效"的变量改用命令行 `-D` 传（命令行 cache 项在配置
开始前即生效），并用 `tc.variables` 补上上游在分支里才设置的路径变量：

```python
def generate(self):
    tc = CMakeToolchain(self)
    # 需要早于 project() → 走 cli_args（见 build()）
    tc.variables["CMAKE_MODULE_PATH"] = os.path.join(
        self.source_folder, "cmake", "modules")

def build(self):
    cmake = CMake(self)
    cmake.configure(cli_args=[f"-DADS_VERSION={self.version}"])
    cmake.build()
```

判据：该变量是否出现在第一个 `project()` 之前的 CMakeLists 语句里 —— 是则
`cli_args`，否则 `tc.variables` 即可。

### 禁止做法

- ❌ 只改 `tc.variables["ADS_VERSION"]` 而不改 `cli_args`——变量在 `project()` 前
  不可见，会持续失败。
- ❌ 跳过 `conan create` 验证（本地 cmake 手跑一遍就认为通过）。

## 验证

```bash
conan create <pkg> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 2>&1 \
  | grep -E 'NOTFOUND|include could not find requested file'
# 无输出即修复
```

## 关联条目

- 相关: E532（HarmonyOS 未归入 UNIX 分支，同属"平台/工具链变量在错误时机取值"族）
- 实证: qt-advanced-docking-system 4.5.0（archives/q/qt-advanced-docking-system/4.5.0）
