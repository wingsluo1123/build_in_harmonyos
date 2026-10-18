# Test Report — indi-dsi 0.4-20221223123028 (MateBook aarch64 真机, OHOS 6.0)

**Status**: PASS
**Date**: 2026-10-15
**Profile**: ohos-aarch64 (clang 15, cppstd=17, libc++)

## Layer1 — test_package 单元探测（test_dsi）

来源: `test_package/test_dsi.cpp`（vendor Util.cpp 自研 tokenize_str 六组断言，纯 std）。

```
mixed_delims: PASS (3 tokens)
consecutive: PASS (2 tokens)
leading: PASS (1 tokens)
trailing: PASS (1 tokens)
empty: PASS (0 tokens)
custom_colon: PASS (3 tokens)
PASS: tokenize_str public helper exercised (6 assertion groups)
```

6/6 断言组全 PASS（conan create.log：reports/conan-create.log）。

## Layer2 — 产物硬断言 + --help best-effort

- 硬断言 `bin/indi_dsi_ccd` 存在: PASS（四件套 bin/xml/udev/firmware 均落 prefix，见下）
- 未签名直接 exec `--help`: **EPERM (rc=126)** — 已知环境行为：对链 libindi 共享库的未签名二进制 exec 被拒，非产物缺陷
- 打包签名后 exec `--help`: **真实 Usage 输出，rc=1（驱动自身退出码）** — EPERM 消失

```
Usage: indi_dsi_ccd [options]
Purpose: INDI Device driver framework.
Options:
 -v    : more verbose to stderr
Configuration successfully saved.
```

## Staging 独立验证（packaging/ tarball）

`packaging/indi-dsi-0.4-20221223123028-ohos-aarch64.tar.gz`（159MB，另 debug 包 57MB）解包至空白目录后**无任何外部 LD_LIBRARY_PATH** 直接执行：

- ELF 签名: binary-sign-tool selfSign 通过
- RPATH: `$ORIGIN/../lib:$ORIGIN/../lib/external`，依赖闭包（libindidriver/libindiAlignmentDriver/libusb/fftw/curl/gsl 等 207 项）全部随包内 lib/ 解析
- exec 结果: 输出真实 INDI 驱动 Usage（见上），rc=1 为驱动约定退出码 — **PASS**

## package() install 落点（prefix 四件套）

| 产物 | 路径 |
|---|---|
| 可执行 | `bin/indi_dsi_ccd` |
| 设备 XML | `share/indi/indi_dsi.xml` |
| udev 规则 | `share/udev/rules.d/99-meadedsi.rules` |
| fx2 固件 | `share/firmware/meade-deepskyimager.hex` |

零 `/lib` 绝对路径泄漏（0004 install 守卫生效）；`src/Util.cpp`、`src/Util.h` 随包。

## 结论

Layer1/Layer2/staging 全部通过；未签名 EPERM 为已知环境行为，打包签名后消除。
