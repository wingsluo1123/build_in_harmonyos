# vtable (vtable-dumper)

列出 C++ 共享库中虚函数表（vtable）内容的命令行工具，常用于发行版维护者与库
开发者做二进制向后兼容（ABI）检查。

## 功能概述

- `vtable-dumper <shared-library>`：列出目标共享库中每个多态类的虚函数表，
  逐槽位打印偏移、槽位内容（函数指针/偏移/typeinfo）。
- `-mangled`：以改名（mangled）形式打印符号；`-demangled`（默认）：打印
  demangle 后的可读形式。
- `-dumpversion` / `-help`：版本与帮助。
- 实现方式：`dlopen` 目标库并遍历其 `_ZTV*` 段，配合 libelf 解析 ELF。

> 上游项目名是 **vtable-dumper**。本仓按平台任务 slug 归档为 `vtable`，
> 因此 Conan 包名/目录名为 `vtable`，构建与安装出的可执行文件仍为
> `vtable-dumper`（见 `commands.json`）。

## OHOS 适配

- **C++ 运行时库名**：上游 Makefile 硬编码 `-lstdc++`，OHOS 只提供 libc++。
  补丁 `0001` 把库名参数化为 `CXXLIB`（补丁本身保留上游默认值 `-lstdc++`），
  本配方在 `build()` 中无条件以 `CXXLIB=-lc++` 覆盖（本仓只面向 OHOS）。
- **依赖 libelf 来自 Conan `elfutils/0.195.1`**，不依赖系统库。设备
  `/lib64/libelf.so` 的 SONAME 是 `libelf.so` 且不导出 `gelf_*`/`elf_version`
  等符号，与 elfutils 的 `libelf.so.1` 不冲突。
- **rpath**：用 `-Wl,--disable-new-dtags` 生成 `DT_RPATH`，使可执行文件的
  rpath 能继承到 `libelf.so.1` 的传递依赖 `libzstd.so.1`，工具无需
  `LD_LIBRARY_PATH` 即可直接运行。
- 未静态链接 `libelf.a`：静态链接会再拉入 zlib（`elf_compress.o` 需要
  `deflateInit_`），静态面扩散，故保留动态链接 + rpath。

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 构建依赖 | `elfutils/0.195.1`（提供 `libelf`）、工具链 `clang`/`make` |
| 运行依赖 | `libelf.so.1` + 其传递依赖 `libzstd.so.1`（均由 elfutils Conan 包提供）、`libc++_shared.so`（系统/工具链提供）、`libc.so` |

## 已知限制

- 工具在失败路径（非 ELF 输入、目标库打不开）也返回退出码 0，调用方需检查
  标准输出内容（本仓 `test_package` 已按输出内容断言）。
- 目标库需能被 `dlopen`：其自身依赖必须可解析。

## 参考资料

- 上游仓库：<https://github.com/lvc/vtable-dumper>
- ABI 实验室：<https://abi-laboratory.pro/>
- 上游版本：1.2（2016-10-04）
- 许可证：LGPL-2.1-or-later
