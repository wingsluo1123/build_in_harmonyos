# libosmo-cc

## 软件描述
libosmo-cc 是 Osmocom 的**呼叫控制（call control）库**：提供 Q.931 风格的呼叫信令消息编解码
（`message`）、会话/SDP 协商（`session`/`sdp`）、RTP 与 G.711 编解码（`rtp`/`g711`）、
以及 socket/endpoint/screen 等辅助模块；是 osmo-msc / osmo-bts 等 Osmocom 栈组件的基础库。

## 功能概述
- 呼叫信令消息的构造/解析（IE 编解码、名称映射表）
- 会话与媒体描述（SDP）协商、编解码能力列表
- RTP 收发与 G.711 A-law/μ-law 转换
- socket / endpoint / screen / misc 辅助 API

## OHOS 适配

### 构建方式
- **配方内直编**（不跑 `./configure`）：上游 2024 快照只有 `configure.ac` + `Makefile.am`，
  没有预生成 `configure`；HarmonyOS 主机有 autoconf 2.72 但**没有 automake/aclocal/libtoolize**，
  `autoreconf -fi` 直接失败（`Can't exec "aclocal"`），上游也没有带 `configure` 的发布包。
- 源码本身很简单（11 个 C 文件、无 config.h、无生成头），配方用 OHOS clang 编译
  `src/*.c` → `libosmocc.so.2.0.0`，并安装与 autotools 构建一致的产物：
  `lib/libosmocc.so{,.2}`、`include/osmocom/cc/*.h`、`lib/pkgconfig/libosmocc.pc`。

### 关键攻坚点
1. **musl 缺 `<sys/time.h>` 传递包含**：`message.c` 直接用 `struct timeval` 但未包含头文件
   （glibc 下由其它头间接带入），编译加 `-include sys/time.h`
2. **libosmocore 头链需要 talloc**：`osmocom/core/utils.h` 使用 `talloc_strdup`，
   include 路径与链接闭包从依赖图里取（libosmocore + talloc + mnl/pcsclite/usb-1.0）
3. **libosmocore 包的 `cpp_info.libs` 不含主体库**：必须显式补 `-losmocore`，
   并用 `-Wl,--no-undefined`（对应上游 libtool 的 `-no-undefined`）确保不再产出带未解析符号的 `.so`
4. **snapshot.debian.org 的内容 URL 以 sha1 结尾**：Conan 无法推断压缩格式，
   `get(..., filename="libosmo-cc.tar.xz")` 显式指定
5. **`.so` / `.so.2` 符号链接与 pkg-config**：autotools/libtool 会安装，配方手工补齐

### 与 Linux 的差异
- 无源码级平台分支；差异集中在 **构建系统缺失（无 automake）** 与 musl 头文件包含习惯

## 依赖关系
- `libosmocore/1.11.0`（及其传递依赖 talloc/mnl/pcsclite/libusb，均来自制品仓）

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.0-git20240818.7864594 | built | 2026-10-17 | snapshot.debian.org 2024 快照；配方内直编；消费者 3/3 |

## 参考资料
- 上游: https://gitea.osmocom.org/cc/libosmo-cc
