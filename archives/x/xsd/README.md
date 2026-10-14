# xsd — Code Synthesis XSD（W3C XML Schema → C++ 代码生成编译器）

## 是什么

**XSD**（Code Synthesis XSD，官网 <https://codesynthesis.com/projects/xsd/>）是一个
W3C XML Schema 编译器：把 `.xsd` schema 文件翻译成**静态类型**的 C++ 数据绑定代码，
并附带一个把 XML 实例解析进该绑定的运行期库。它是许多 C++ XML 工具链的上游依赖
（Xerces-C++ 生态之外最常用的 schema 编译器之一）。

命令行形态是**命令式**子命令（不是长选项开关）：

```
xsd cxx-tree   …   # 生成 C++/Tree 映射（常驻内存对象树，tree 模式）
xsd cxx-parser …   # 生成 C++/Parser 映射（SAX 式事件流 + pimpl 骨架，map 模式）
xsd version    …   # 自报版本
```

## 功能概述

- **C++/Tree（tree 模式）**：把 XML 文档一次性解析成类型化的对象树，支持序列化回写、
  流输出（`--generate-ostream`）、比较运算（`--generate-comparison`）、多态、
  `xsi:type`、base64 二进制成员等；运行期头文件是 `<xsd/cxx/tree/…>`。
- **C++/Parser（map 模式）**：事件驱动、边解析边消费，骨架（`-pskel`）与实现
  （`-pimpl`）分离，适合大文档与流式处理；运行期头文件是 `<xsd/cxx/parser/…>`。
- 两种模式的生成代码都链接 **Xerces-C++** 做 XML 解析/校验。
- 附带 `libxsd` 头文件运行期库（**无 .so/.a 交付物**）、示例与文档。

## 依赖关系

| 类型 | 依赖 | 版本 | 说明 |
|---|---|---|---|
| 编译期硬依赖 | `xerces-c` | 3.2.5 | 唯一 conan 依赖；+dep 发行包捆绑了 libcutl/libxsd-frontend/build，但 README 明写 "all its dependencies (except Xerces-C++)" |
| 编译期（捆绑） | libcutl 1.8.1、libxsd-frontend 2.0.0、build-0.3 | — | 随 `+dep` tarball 一起构建，不进 conan 依赖图 |
| 运行期 | Xerces-C++ | — | `bin/xsd` 静态链接 `libxerces-c.a`；生成代码的使用者同样需要 xerces |
| 构建工具 | GNU make ≥3.81、bash ≥2.00、clang/g++ | — | 上游 README 明列 |

## OHOS / HarmonyOS PC 适配要点

1. **libc++ `<version>` 遮蔽**：OHOS NDK libc++ 的 `<cstddef>` 无条件
   `#include <version>`，而上游把 `libcutl/version`、`libxsd-frontend/version`
   两个纯文本版本标记文件放在被 `-I` 的目录里 ⇒ 标准库头被同名文件遮蔽。
   libstdc++ 不这样包含，故 Linux/CCI 构建碰不到。修法见
   `4.0.0/patches/0001-libcxx-version-header-collision.patch`。
2. **libc++ 不从传递包含带出 `<ostream>`**：`libxsd-frontend` 的
   `semantic-graph/elements.cxx` 在 `basic_ostream` 尚不完整时定义
   `operator<<(std::wostream&, Path const&)` ⇒ 成员 `operator<<(const void*)`
   不可见。修法与上游提交 `5029f866` / CCI `0002-missing-include.patch` 同源。
3. **Xerces-C++ 3.2**：本包依赖 `xerces-c/3.2.5`，上游三组编码测试的期望值
   需要按 Debian bug #881108 的上游补丁更新（CCI `0110` 同源）。
4. **构建系统不是 autotools**：根 `makefile` + 自带 `build-0.3` make 体系；
   `configuration-dynamic.make` 已随 `+dep` 包预生成（非交互），
   `build-0.3/system/configure`（2009 版 `config.guess`）在设备上 rc=1，但该路径本包不触发。
5. **C++ 标准**：profile `compiler.cppstd=17`，配方把 `-std=c++11` 放进
   `extra_cxxflags`（排在 cppstd 之后，clang 取最后一个），与 CCI 一致。
6. **并行度**：`tools.build:jobs` 缺省自限 4（`os.cpu_count()`=20 与容器 affinity=8 不符）。

## 与 Linux 的差异 / 已知问题

- 无系统级差异阻塞；全部为 libc++ 头文件可见性与 Xerces 3.2 期望值两类可移植性补丁，
  **不含任何 `__OHOS__` 平台宏或平台特判**。
- `tree/binary/{cdr,polymorphic,xdr}` 三组上游测试按 `xsd_with_ace` 条件注册，
  +dep 包预生成 `xsd_with_ace := n` ⇒ 默认不在 `make test` 内（需 ACE 库）。
- `make dist` 目标未验证（本包不产出 dist）。

## 参考资料

- 官网 / 项目页：<https://codesynthesis.com/projects/xsd/>
- 官方下载目录：<https://codesynthesis.com/download/xsd/4.0/>
- XSD 手册（上游随包文档，也安装到 `share/doc/xsd/doc`）
- conan-center-index 配方：<https://github.com/conan-io/conan-center-index/tree/master/recipes/xsd>
- Xerces-C++：<https://xerces.apache.org/xerces-c/>
