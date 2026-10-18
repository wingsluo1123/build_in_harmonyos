# osmo-libasn1c 0.9.38 HarmonyOS PC 适配笔记

## 结论

- HarmonyOS PC（aarch64, OHOS clang 15, musl）构建通过。
- `conan create` 返回 0。
- 消费者程序通过公开头文件编译、链接并运行，输出
  `LIBASN1C_CONSUMER_OK`。
- 交付 `libasn1c.so.1.0.2`、`libasn1c.so.1`、`libasn1c.so`、
  公开头文件和 `libasn1c.pc`。

## 为什么配方内直接编译

Debian 的 `0.9.38.orig.tar.xz` 只有 `configure.ac` 和 `Makefile.am`。
构建机没有 `automake/aclocal/libtoolize`，无法生成 `configure`。
上游源码是一个稳定的 asn1c 运行时文件集合，没有生成头文件或 config.h，
因此配方使用宿主 OHOS clang 直接编译 `src/*.c`，并按上游
`LIBVERSION=1:2:0` 安装 libtool 对应的 `libasn1c.so.1.0.2`。

## 关键兼容点

1. **双 include 路径**

   应用常写 `#include <asn1c/INTEGER.h>`，但库内头文件互相使用
   `#include <asn_application.h>`。因此 `cpp_info.includedirs` 同时包含
   `include` 和 `include/asn1c`，与上游 `libasn1c.pc` 一致。

2. **`talloc_asn1_ctx` 的弱链接语义**

   `asn_internal.h` 声明 `extern void *talloc_asn1_ctx`，共享库引用但
   不定义它。检查 Debian 官方 arm64 `libasn1c.so.1.0.2`，该符号同样是
   `U talloc_asn1_ctx`；它由 asn1c 生成的应用程序定义。若构建共享库时
   强加 `--no-undefined`，会错误地拒绝这一定义。

3. **talloc 公开头文件依赖**

   公共头 `asn_internal.h` 直接包含 `<talloc.h>`，因此 Conan 消费者必须
   获得 `talloc/2.4.4` 的头文件和链接目录。测试包显式声明该依赖，避免
   Conan 2 test-package 的传递 include 目录不完整。

## 验证命令

```text
conan create archives/o/osmo-libasn1c/0.9.38 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

结果：

```text
CREATE_RC=0
LIBASN1C_CONSUMER_OK
```
