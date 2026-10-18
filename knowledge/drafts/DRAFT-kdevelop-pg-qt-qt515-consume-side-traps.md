# DRAFT-kdevelop-pg-qt-qt515-consume-side-traps

## 在 qt5-qtbase/5.15.2.2 上做 CMake+Qt5 消费方：四个必踩的坑

以 `kdevelop-pg-qt/1.90.92` 的适配过程为样本。四个坑彼此独立，而且**每一个都会让
你误以为是另一个问题**——所以按"撞到的顺序"记录，附各自的判定方法与修法。

---

### 坑 ①：包内 CMake config 烙死了构建树路径

```
CMake Error at .../p/lib/cmake/Qt5Core/Qt5CoreConfig.cmake:14 (message):
  The imported target "Qt5::Core" references the file
     ".../p/../b//mkspecs/linux-clang"
  but this file does not exist.
```

根因：`Qt5CoreConfigExtrasMkspecDir.cmake` 里写着
`${_qt5Core_install_prefix}/../b//mkspecs/linux-clang` —— 那个 `/../b/` 是
**configure 期的构建目录**，包发布后不存在。上游已在 `5.15.2.3` 修（repoint 到
包内副本 + 拒绝打包泄漏的 config）；`5.15.2.2` 上只能消费方自己处理。

**别踩的坑**：该 config 用
```cmake
get_filename_component(_qt5Core_install_prefix "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)
```
**按自身位置反推前缀** —— 所以"把它拷到自己的 build 目录再改路径"是错的：
前缀会变成你的 build 目录，报 `<build>/include` 不存在（实测踩过）。

### 坑 ②：CMakeDeps 生成的 Qt5 配置不带上游宏

试过用 `CMakeDeps` + `cmake_file_name = "Qt5"` 重新生成一套干净的 Qt5 配置：
`Qt5::Core` / `Qt5::Test` 目标都有了，但构建时报

```
CMake Error at kdev-pg/CMakeLists.txt:7 (QT5_ADD_RESOURCES):
  Unknown CMake command "QT5_ADD_RESOURCES".
```

因为上游宏（`Qt5CoreMacros.cmake` 的 `qt5_add_resources` / `QT5_ADD_RESOURCES`
等）在包内的 `lib/cmake/Qt5Core/` 里，CMakeDeps 不会生成。另外 ECM 的
`ECMQueryQt.cmake:51` 走的是**模块级** `find_package(Qt5Core QUIET)` 并要求
`Qt5::qmake` 目标去跑 `qmake -query` —— 生成物里也没有。

> 顺带一个反直觉点：一旦你写了 `conan_cmakedeps_paths.cmake`，`conan_toolchain`
> 就不再走它自己的 else 分支，**生成器目录也不会自动进搜索路径**，于是连
> `Qt5Config.cmake` 都找不到（报 "Could not find a package configuration file
> provided by Qt5"）。

### 坑 ③：`find_program` 的 `*-NOTFOUND` 等于没禁

想禁用宿主 flex/bison、强制用源码包自带的生成文件，写法是

```cmake
set(FLEX_EXECUTABLE FLEX_EXECUTABLE-NOTFOUND)   # ✗ 无效
```

`find_program` 见到值是 NOTFOUND 会**重新搜索** → 宿主 flex 照样被找到并重新生成
lexer，而新生成的骨架与上游 `.ll` 用户代码不兼容：

```
kdev-pg-lexer.ll:255:12: error: use of undeclared identifier 'yymore_used_but_not_detected'
```

正解是**空值**（`-DFLEX_EXECUTABLE=`）：变量已定义 → 跳过搜索，且 `IF()` 判假 →
走上游 `ELSE` 分支用随包生成文件。

### 坑 ④：没有 RUNPATH 的 ELF，只能靠内联的 `LD_LIBRARY_PATH`

测试二进制与生成器都没有 RPATH/RUNPATH 条目（`llvm-readelf -d` 为空），运行时
只能靠环境变量：

```
Error loading shared library libQt5Test.so.5: (needed by .../tests/testlocationtable)
```

两个细节都踩过：

- `VAR=... cmd1 && cmd2` 的内联变量**只作用于 cmd1** ——
  `LD_LIBRARY_PATH=... cd X && kdev-pg-qt ...` 里生成器拿不到变量（退出码 127，
  `/system/bin/sh: kdev-pg-qt: inaccessible or not found`）→ 必须
  `sh -c 'cd X && kdev-pg-qt ...'`；
- conan 的 `Environment().apply()` 在本平台实测**没有**传到 `self.run` 的子进程
  → 干脆两处都改为命令行内联。

---

## 正解：qt-prefix 镜像

在 build 目录里镜像一个可用的 qtbase 前缀：

- 除 `lib/` 外**全部符号链接**到真实包；
- `lib/` 下除 `cmake` 外也符号链接；
- 只把 `lib/cmake` 做**真实拷贝**，并把 `/../b//` 归一成 `/`。

这样 `<mirror>/lib/cmake/Qt5Core/../../../` == `<mirror>/`（前缀推导对了），而
`<mirror>/mkspecs`、`<mirror>/include`、`<mirror>/lib/libQt5Core.so` 都是指向真实包的
符号链接（都"存在"）→ 上游真实 config **与宏**全部可用，ECM 的模块级查找也满足。
实现见 `archives/k/kdevelop-pg-qt/1.90.92/conanfile.py` 的 `_build_qt5_prefix()`。

## 附带两个（同一趟撞到，也一并记下）

| 现象 | 根因 | 修法 |
|---|---|---|
| `Compatibility with CMake < 3.5 has been removed` | 上游是 `cmake_minimum_required(VERSION 2.8.12)`（第 7 行） | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，**必须以 cache 变量/`-D` 传**（toolchain 的普通 `set()` 晚于第 7 行执行，实测无效） |
| 19 处 `ISO C++17 does not allow 'register'` | 随包 lexer 是 flex 2.5 时代产物 | `-Wno-register` 降级 |

## 验证

`conan create` 全绿：上游 CTest **3/3 通过**（`100% tests passed, 0 tests failed
out of 3`）；消费侧真跑生成器处理上游 `examples/fact/fact.g` → 产出 9 个文件
（`factparser.cpp/h`、`factast.h`、`factast-fwd.h`、`factvisitor.cpp/h`、
`factdefaultvisitor.cpp/h`、`facttokentype.h`）。

## 教训

1. 见到"引用了不存在的文件"先看**路径里是不是有构建目录残留**（`/../b/` 之类）；
2. 要找**文件名里的量**（`readelf -d`、`grep`）而不是看报错表象 —— 四个坑里有三个
   的报错都在"别处"；
3. 上游宏与 config 是**两件事**：能生成目标 ≠ 有宏；模块级查找（`find_package(Qt5Core)`）
   与组件级查找（`find_package(Qt5 COMPONENTS Core)`）也是两件事。
