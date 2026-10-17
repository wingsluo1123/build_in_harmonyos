# pesign 116 适配说明（HarmonyOS PC / ohos-aarch64）

## 1) 身份与源

- 上游：`https://github.com/rhboot/pesign`（tag **116**，与平台清单一致）
- 源：`pesign-116.tar.gz`，sha256 `339d141abe3314322311b3c4259175ef937160ac25be4c219495225917c7cdaa`
- 语言 / 构建：**C** / 手写 Makefile 体系（`Make.defaults` + `Make.rules` + `src/Makefile`）→ **不需要 autoreconf**
- 产物：`bin/pesign`（191,104 B）、`bin/efikeygen`（170,624 B）、`bin/authvar`、`bin/pesign-client`、
  `bin/pesigcheck`、`bin/pesum`

## 2) 依赖（上游 `Make.defaults` 的 `PKGS = efivar nspr nss nss-util uuid`，部分目标另加 `popt`）

| 依赖 | 制品仓 | 说明 |
|---|---|---|
| `efivar` | `efivar/39` ✓ | 包内 `lib/libefivar.so` + `libefiboot.so` + `libefisec.so` |
| `nspr` | `nspr/4.37` ✓ | `libnspr4` / `libplc4` / `libplds4` |
| `nss` | `nss/3.118.1` ✓ | 真正含 NSS 符号的是 **`libnss3.so`** |
| `popt` | `popt/1.19` ✓ | |
| `uuid` | `uuid/2.40.1` ✓ | 只有静态 `libuuid.a` |
| `nss-util` | **制品仓无独立包** ✗ | 由配方在生成器目录补一个最小 `nss-util.pc` 指向 `nss` |

## 3) musl 侧需要补的 glibc 扩展（垫片方案）

musl 缺：`error_t`（类型）、`qsort_r`、`secure_getenv`、`program_invocation_short_name/name`。
clang 15 在 C99 下把"隐式声明 + int→指针"判为**硬错误**，所以不能只当警告放过。做法：

- 配方生成 **`<source>/include/conan_musl_shim.h`**（该目录已在**每个**编译单元的 `-I` 里），
  由补丁在 `Make.defaults` 的 CFLAGS 行加 `-include conan_musl_shim.h`（**不需要绝对路径**）；
- 头里声明上述符号（`loff_t` 用 musl 自己的 `__DEFINED_loff_t` 机制守卫，避免与 `bits/alltypes.h` 撞）；
- 另生成 `conan_musl_shim.c` 编成 `.o` 交给链接：**实现 `secure_getenv`**（musl 连实现都没有 →
  实测 `undefined symbol: secure_getenv`），并给 `program_invocation_*` 两个 **weak 定义**兜底
  （libc 若有强定义会被优先采用，不冲突）。

## 4) 链接参数（上游 `.pc` 与包内实际库名不符）

上游 `nss.pc` 写的是 `-lnss -lssl -lsmime -lnssutil -lsoftokn -lfreebl -lnssckfw -lnssdbm -lsqlite`，
而 conan 的 nss 包里是 `libnss3.so` / `libnssutil3.so` / `libfreebl3.so` / `libsmime3.so` / `libssl3.so` /
`libsoftokn3.so` / `libsqlite3.so` 等 → 于是报一串 `undefined symbol: PK11_* / CERT_* / SECKEY_*`
（实测这些符号就在 `libnss3.so` 里）。处置：

- 配方**扫描各依赖包 `lib/` 下的实际共享库**，按其真实文件名生成 `-l` 列表；
- 并用 `LDFLAGS` **显式带 `-L` 与 `-Wl,-rpath`**（运行期也要能加载，消费者环境里直接跑二进制时
  不写 rpath 会 `Error loading shared library libfreebl3.so`，rc=127）；
- `RANLIB=llvm-ranlib`（conan 环境给的是 `clang-ranlib`，本工具链里没有该名字）。

## 5) 补丁（`patches/0001-reallocarray-portability.patch`，8 个 hunk）

| 位置 | 改动 | 原因 |
|---|---|---|
| `include/libdpe/libdpe.h` | 补 `#include <sys/types.h>` | 该头用了 `loff_t` 却没包含提供它的头 |
| `src/compiler.h` | `#ifdef __ALIGN` → `#undef __ALIGN` | musl 头里已有同名宏，重定义是 macro-redefined |
| `src/list.h`、`src/password.c` | `reallocarray` → 等价 `realloc` | musl 不声明 `reallocarray`（隐式声明成 int → 指针赋值报错） |
| `Make.defaults` | `-Werror`→`-Wno-error`；`-fshort-wchar`→`-D_GNU_SOURCE -include conan_musl_shim.h` | `-fshort-wchar` 会让 `wchar_t` 与 sysroot 的 `bits/alltypes.h` 冲突 |
| `src/Makefile` | 构建目标去掉 man 页；man 安装行加 `-` 前缀 | `Make.rules:57` 硬编码调用 `mandoc`，本环境没有该工具 |

## 6) 测试

- **上游 116 没有测试**（如实声明：源码包内无 `tests/`，117 才有）。
- 配方内两条**真跑**：`pesign --help`、`efikeygen --help` 都必须 rc=0 且有输出 ✓。
- 消费者 `test_package/check_pesign.py` **6 项**（全部离线）：产物齐备 / ELF 头 / 两条真跑 / 许可证 / 证据。
  末行打印 `checks=/fails=/skips=`；仅环境原因才计入 skips 且**不计入通过**。
- **边界如实说明**：真正的签名/校验需要 NSS 证书库与 EFI 变量环境，沙箱不具备 → 本包验证的是
  "产物可用 + CLI 真跑得起来"，**不代表签名流程已验证**。

## 7) 如实记录的偏离

1. `secure_getenv` 由垫片实现为 `getenv`（musl 无该扩展；pesign 不是 setuid 程序）。
2. man 页不构建、不安装（依赖 `mandoc`，非适配必需品）。
3. `-Werror` 降级为 `-Wno-error`（换 libc 必然产生宏/类型类警告，其本身不是适配问题）。
4. 去掉上游的 `-fshort-wchar`（musl 的 `wchar_t` 是 unsigned int，加它会与 sysroot 冲突）。

## 8) 实测（本地 conan create）

`rc=0`；构建完成并产出 6 个二进制；配方内两条真跑 ✓；消费者 `checks=6 fails=0 skips=0 / RESULT: PASS`。
