# kcharselect 26.04.0 — 配方写了 INSTALL_RPATH ≠ 产物有 RPATH

## 现象

配方里明确设置了 RPATH：

```python
tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = "-Wl,-z,max-page-size=0x1000 -Wl,--disable-new-dtags"
tc.variables["CMAKE_BUILD_RPATH"] = rpath      # 全部依赖 lib 目录
tc.variables["CMAKE_INSTALL_RPATH"] = rpath
```

CMakeCache 确认变量已生效（`CMAKE_SKIP_RPATH=NO`、`CMAKE_SKIP_INSTALL_RPATH=NO`），
但最终产物：

```
$ readelf -d <package>/bin/kcharselect | grep -E 'RPATH|RUNPATH'
$ echo $?
1            # 一个都没有
```

同时 `CMakeFiles/kcharselect.dir/link.txt` 里**没有** `-rpath`，
`cmake_install.cmake` 里也没有任何 rpath 调用。

## 根因

1. CMake 的安装期 RPATH 处理是 `file(RPATH_CHANGE OLD_RPATH NEW_RPATH)` 语义——
   **改写**链接期已经写进 ELF 的 RPATH 字符串，而不是新增一个条目。没有既有条目就
   无从改写。
2. 链接期是否产出 RPATH 取决于链接行。当依赖库以**绝对路径**入链
   （Conan CMakeDeps / 裸绝对路径的典型形态）时，CMake 不会把
   `-Wl,-rpath,<dir>` 加进 link.txt → ELF 里没有 RPATH → `--disable-new-dtags`
   没有作用对象。
3. 于是"配方设置了 CMAKE_INSTALL_RPATH，所以产物能自己找到依赖"是一个**未验证的假设**。

## 修复 / 正确做法

1. **实测**：`readelf -d <bin> | grep -E 'RPATH|RUNPATH'`；文档与 PR 只写实测结论。
2. **运行期依赖 Conan runenv**：`package_info()` 里为自身与全部依赖
   `runenv_info.prepend_path("LD_LIBRARY_PATH", <pkg>/lib)`；使用方
   `conan install ... -g VirtualRunEnv` 后 `source conanrun.sh` 再运行。
3. **不要**为了让产物"自包含"而把 RPATH 指向 conan 缓存绝对路径——那正是不便携的
   根源（与 DT_NEEDED 绝对路径净化同一个问题，见
   `DRAFT-14403-registry-so-no-soname-dynstr-normalize-resign`）。
4. 预期现象：CI 的 L2 冒烟（不加载 runenv 直接跑 `--version/--help`）对 GUI/Qt 应用
   会失败并 skip（非阻断）——这不是产物坏了。

## 验证

kcharselect/26.04.0：`readelf -d` 无 RPATH/ RUNPATH；`link.txt` 无 `-rpath`；
`conan install -g VirtualRunEnv` + `source conanrun.sh` 后
`kcharselect --version/--help/--author/--license` 全部正常，消费者用例
（含 OHOS closure 加载）4 用例 / 5 断言全通过。
