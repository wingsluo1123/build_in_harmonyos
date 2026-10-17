# libosmo-cc 0.0-git20240818.7864594 适配笔记

## 编译环境
- 构建方式: 配方内直编（OHOS clang 15.0.4，musl，aarch64）
- 编译日期: 2026-10-17
- 依赖: `libosmocore/1.11.0`（含 talloc/mnl/pcsclite/libusb 传递依赖）

## 版本说明
- 上游: https://gitea.osmocom.org/cc/libosmo-cc（GPL-2.0-or-later）
- 源码: snapshot.debian.org 的 `0.0~git20240818.7864594` orig 包
  sha256 `bb4dd720f7daaa9a0ce8a3cbdb4d9f70fc2e90c47afbc07f135c5dc14745b8cd`（44956 B）
- 平台任务版本 `0.0-git20240818.7864594`（Debian `+`/`~` 规范化为 `-`）

## 为什么不用 autotools
- 快照只有 `configure.ac` + `Makefile.am`，无 `configure`
- 设备有 autoconf 2.72/autoreconf，但 **无 automake/aclocal/libtoolize** → `autoreconf -fi` 失败
- 上游无 release/tag（Gitea API 空）→ 没有带 configure 的发布包
- 源码简单（11 个 .c、无 config.h、无生成头），配方直编可完整复现 autotools 产物

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | `BadZipFile: File is not a zip file` | snapshot 内容 URL 以 sha1 结尾，Conan 无法识别 tar.xz | `get(..., filename="libosmo-cc.tar.xz")` |
| 2 | `talloc.h file not found` + `incompatible integer to pointer` | `osmocom/core/utils.h` 使用 talloc；talloc 头不在路径 → `talloc_strdup` 隐式声明 | include 路径取全部 host 依赖（libosmocore+talloc+…） |
| 3 | `incomplete type 'struct timeval'` | `message.c` 未 include `<sys/time.h>`（glibc 间接带入，musl 不带） | 编译加 `-include sys/time.h` |
| 4 | 消费者链接 `undefined reference: osmo_log_info/osmo_timer_*` | **libosmocore 包的 `cpp_info.libs` 不含主体库**，链接只得到 talloc/mnl/pcsclite/usb-1.0 | 显式补 `-losmocore`；构建加 `-Wl,--no-undefined`（对齐上游 `-no-undefined`） |
| 5 | `-losmocc` 找不到库 | 只安装了 `libosmocc.so.2.0.0` | 补 `.so.2` / `.so` 符号链接（失败时回退为复制） |
| 6 | 无 pkg-config | autotools 会生成 `libosmocc.pc` | package() 按上游 `libosmocc.pc.in` 字段生成 |

## 验证结果
```text
CREATE_RC=0
package(): libosmocc.so.2.0.0 + .so/.so.2 + libosmocc.pc + 11 headers
[ok] public header OSMO_CC_VERSION is OSMOCCv1
[ok] osmo_cc_msg_value2name(SETUP_REQ) returns a name
[ok] IE value/name round-trip
LIBOSMO_CC_CONSUMER_CHECKS=3 FAILURES=0
LIBOSMO_CC_CONSUMER_OK
```

## 上游测试清点（R51）
```text
find . -maxdepth 2 -type d -iname "*test*"   → 无
grep check_PROGRAMS/TESTS Makefile.am        → 无
```
上游确无测试套件；消费者用例由 `test_package/test_cc.c` 承担。

## 交付物
- `lib/libosmocc.so.2.0.0`（soname `libosmocc.so.2`）+ `.so.2`/`.so`
- `include/osmocom/cc/*.h`（11 个头文件）
- `lib/pkgconfig/libosmocc.pc`

## 注意事项
1. 直编绕过了 autotools，已在 conanfile/notes/PR 中说明原因；编译/安装产物与 autotools 一致。
2. 上游两个 `AC_DEFINE`（`HAVE_ORTP_LOG_DOMAIN`、`RTP_SIGNAL_PTR_CAST`）只在检测到 ortp 时使用，
   `src/` 未引用，故本包不引入 ortp。
