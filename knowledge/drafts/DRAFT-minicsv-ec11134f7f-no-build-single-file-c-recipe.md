# 无构建系统单文件 C 库的 Conan 配方模式（build() 注入最小 CMakeLists）

- **草稿 ID**: DRAFT-minicsv-ec11134f7f-no-build-single-file-c-recipe
- **来源**: minicsv ec11134f7f HarmonyOS PC（aarch64-linux-ohos）适配
  （上游仅 minicsv.c / minicsv.h / minicsv-test.c，无 Makefile / configure / CMakeLists）
- **分类**: conan / packaging / no-build-system / single-file-library
- **状态**: 本地草稿（路径 B 知识库扩展，随 minicsv PR 提交）

## 问题 / 错误签名

无上游构建系统的**单文件 C 库**（上游只交付 .c/.h，没有任何构建文件）按常规
Conan 流程适配时，`conan-init` 无法选择构建系统模板，直接手写配方会遇到三类门禁：

1. **G1 配方完整性**：`conan-verify` 报 `conanfile.py 缺少: export_sources() 方法`
   与 `缺少: 补丁应用调用`——即使 `conandata.yml` 的 `patches: {}` 为空也必须声明
   `export_sources()` + build() 内 `apply_conandata_patches(self)`。
2. **L0k/R38 误判 CLI**：若在 build() 内注入的 CMakeLists.txt 写成
   `install(TARGETS minicsv ARCHIVE DESTINATION lib ... RUNTIME DESTINATION bin)`，
   L0k 的 `detect_bindirs.py`/`grep RUNTIME DESTINATION bin` 会把**纯静态库**误判为
   命令行工具，报 `CLI tool detected but commands.json missing (R38)` →
   `commands_json_r38`（E424 只覆盖 CLI 正向，不覆盖静态库反向误判）。
3. **L0d 空壳测试**：test_package 的 test() 只 `cmake.test()` 会被 L0d 判
   `stub_test_method`——必须追加 `self.run(...)` 实际执行消费者二进制
   （与 E472 同向要求）。

## 根因

1. 无构建系统库没有"模板可选的构建族"，conan-init 模板路由失败，配方需手写；
   G1 是结构检查，把 export_sources/补丁应用调用列为必填字段（同 E257 的
   build() 必填逻辑，但这里是**编译型**单文件库而非 header-only）。
2. L0k 的 CLI 判定是源码级静态扫描（`RUNTIME DESTINATION bin` / `dst="bin"`），
   注入 CMakeLists 字符串同样会被扫到；静态库实际无 RUNTIME 产物，声明即误报。
3. L0d 检查 test() 是否含 `self.run`，只跑 CTest 不被识别为真实执行。

## 方案

`archives/m/minicsv/ec11134f7f/conanfile.py`（完整可复刻）：

```python
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save

class MinicsvConan(ConanFile):
    name = "minicsv"; version = "ec11134f7f"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}; default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)          # G1：即使无补丁也声明

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)           # G1：补丁应用调用（无补丁时为空操作）
        # 静态库专用：只写 ARCHIVE/LIBRARY，绝不写 RUNTIME DESTINATION bin（防 L0k 误判）
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
             """cmake_minimum_required(VERSION 3.15)
project(minicsv C)
add_library(minicsv minicsv.c)
target_include_directories(minicsv PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
install(TARGETS minicsv ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
install(FILES minicsv.h DESTINATION include)
""")
        cmake = CMake(self); cmake.configure(); cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["minicsv"]
```

test_package/conanfile.py test()：

```python
def test(self):
    cmake = CMake(self)
    cmake.test()
    # L0d：必须 self.run 实际执行消费者二进制（仅 cmake.test() 会被判空壳）
    self.run(os.path.join(self.cpp.build.bindirs[0], "test_minicsv"), env="conanrun")
```

## 验证

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` → rc=0，
  G1-G4 全过，test_package 1/1 通过（minicsv 实测）。
- `finish ... published` → W3 本地 CI（build_and_test.sh）L0/L1/L2/L4/L5 全绿，
  `.ci-result.json exit_code=0`（minicsv 实测，JC 基线隔离见库内审计）。
- 鸿蒙特有测试 reports/harmonyos-test.c 链接打包产物，`__OHOS__=1`、
  HongMeng Kernel 1.12.0 aarch64，12 项断言两次运行 PASS。

## 适用边界

- 适用：无任何构建系统（无 Makefile/configure/CMakeLists/Meson）的单文件 C/C++
  库；与 E392（有 raw Makefile）互补——E392 处理有 Makefile 的三陷阱，本条目
  处理完全无构建文件、需注入 CMakeLists 的场景。
- 不适用：header-only（走 E257 no-op build）、有 CMake 上游（走 cmake 模板）、
  有 Makefile（走 E392）、数据/资源包（E241/E255/E281）、CLI 工具包（E424）。

## 反例 / 限制

- 若上游单文件库是 C++ 且含模板/内联实现，注入 CMakeLists 时
  `project(minicsv C)` 须改 `CXX` 并加 `set(CMAKE_CXX_STANDARD 17)`。
- 注入 CMakeLists 属"配方内生成构建文件"，不产生 patches/ 补丁；上游 .c 如需
  平台宏修改应走 patches/ 而非改注入字符串（R8 口径）。
- 本条目不覆盖 GitHub 下载超时类网络问题——那是 E347（预置 conan 下载缓存）。

## 查重差异

- 与 E257：E257 是 header-only **无编译**（no-op build + copy 头文件）；本条目是
  编译型单文件 C 库（真实 add_library 编译 .c 为静态库）。
- 与 E392：E392 有 raw Makefile（BadZipFile/compiler_executables/make cwd 三陷阱）；
  本条目完全无构建文件，注入 CMakeLists 是唯一构建入口。
- 与 E424：E424 是 CLI 工具正向要求 commands.json；本条目是**静态库反向**——
  RUNTIME DESTINATION bin 被 L0k 误扫为 CLI。
- 与 E271：E271 是单文件可执行资产按归档解压失败；本条目是单文件**源码库**配方。
