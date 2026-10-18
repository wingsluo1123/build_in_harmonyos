# libsmpp34 1.14.4 HarmonyOS PC 适配笔记

## 结论

- `conan create` 返回 0。
- 上游 `test_pdu` 27 个测试程序全部实际运行通过。
- 消费者执行 `BIND_TRANSMITTER` PDU pack/unpack 往返，输出
  `LIB_SMPP34_CONSUMER_OK`。

## 构建

Debian orig 包只有 `configure.ac` / `Makefile.am`，没有预生成的
`configure`。库本身只有 7 个 C 文件，直接使用 OHOS clang 构建：

```text
LIBVERSION=3:1:2
real name: libsmpp34.so.1.2.1
soname:    libsmpp34.so.1
```

## 关键兼容点

公开头文件 `smpp34_structs.h` 不是自包含的，它通过：

```c
#include "def_frame/dad.frame"
```

引用上游的 25 个 `.frame` 结构定义文件。因此制品不能只安装
`smpp34*.h`，还必须安装：

```text
include/def_frame/*.frame
```

缺少这些文件时库本身能构建，但任何消费者包含
`smpp34_structs.h` 都会失败。本配方已补齐并加入消费者验证。

## 上游测试

`test_pdu/Makefile.am` 定义 27 个 PDU 测试程序，每个程序由
`core.c + <pdu>_test.c` 构成。对安装后的 Conan 制品编译运行：

```text
SMPP34_UPSTREAM pass=27 fail=0 total=27
```

`test_apps` 的 XML/TCP 示例依赖 libxml2 和网络环境，不属于库本体；
本 PR 不把它作为库功能门槛。
