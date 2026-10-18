# mfgtools (NXP uuu) 1.5.243 适配笔记

## 结论速览
- **上游**：NXPmicro/mfgtools，产物名 **`uuu`**（Universal Update Utility，i.MX 系列烧写工具）
- **类型**：C++（`libuuu` 静态库 + `uuu` CLI）/ CMake
- **产物**：`bin/uuu`（musl 动态 ELF64/AArch64，5720640 字节）+ `licenses/LICENSE`（BSD-3-Clause）
- **依赖**：libusb 1.0.27 / zstd 1.5.7.1 / tinyxml2 11.0.0 / zlib 1.3.2 / bzip2 1.0.8 / openssl 3.5.6
  —— **全部已在仓库归档**（口径：算依赖先扣掉仓库已有）
- **上游测试**：**0 个** → 配方里补 `uuu -h`；消费者 6 项
- **状态**：built（本地 conan create 全绿：编译 ✓ + 消费者 6/6 ✓）

## 源码来源（只以 release 资产发布）
平台条目名是 `mfgtools`，但上游仓库的**源码不在 tag 里**，只在 release 资产：
```
https://github.com/NXPmicro/mfgtools/releases/download/uuu_1.5.243/uuu_source-uuu_1.5.243.tar.gz
sha256 = dee3be0f337c631bf93232f5ea42440f07782ce005c9219a14731d66bbe83658
```
该 URL 与 sha256 取自 AUR 的 PKGBUILD，本地实测下载后 **sha256 完全一致** ✓。

## 五处必须知道的坑（10 轮 CI 才打通）

### 1) `pkg_check_modules(... REQUIRED ...)` 找不到依赖
上游 `libuuu/CMakeLists.txt` 与 `uuu/CMakeLists.txt` 用 pkg-config 找 libusb-1.0 / libzstd /
tinyxml2 / zlib → conan 下必须 **`PkgConfigDeps(self).generate()`** 生成 `.pc`，否则直接
`The following required packages were not found`。

### 2) `bzlib.h` 找不到
上游 `include_directories(...)` 里**漏了 BZip2**（在普通 Linux 上靠 `/usr/include` 蒙混过去）→
conan 环境下必须补 BZip2 的 include。

### 3) `base64_encode` 未声明（最隐蔽的一处）
`libuuu/http.cpp` 里 `base64_encode` 的**定义**在 `#ifdef UUUSSL`（第 64 行起），而**使用处**（506 行）
**没有同等守卫**。conan 下 `find_package(OpenSSL)` 不命中 → `OPENSSL_FOUND` 为假 → 上游不定义
`UUUSSL` → 使用处报 `use of undeclared identifier 'base64_encode'`。
→ 配方里注入：**无条件** `set(UUUSSL "-DUUUSSL")`，并把 OpenSSL 的 include **直接**塞进
`include_directories`（上游只在 `if(OPENSSL_FOUND)` 里才把 `OPENSSL_INCLUDE_DIR` 赋给
`UUUOPENSLL_INCLUDE_DIR`，靠它没用）。

### 4) 运行时 `Error relocating …: <tinyxml2 符号> symbol not found`
上游两个 CMakeLists 顶部都有 **`set(CMAKE_SKIP_RPATH ON)`** → 我设的 `CMAKE_BUILD_RPATH` /
`CMAKE_INSTALL_RPATH` **全部被忽略**（实测二进制里没有任何 RPATH）→ 运行期加载器解析到别处的同名 so。
→ 改用**直接的链接器参数** `-Wl,-rpath,<dep>/lib`（不受 CMake 的 rpath 逻辑与 SKIP_RPATH 影响），
测试运行时再叠加 `LD_LIBRARY_PATH`。

### 5) `uuu -h` 在本环境 abort（环境限制，如实记录）
```
libc++abi: terminating due to uncaught exception of type std::runtime_error: Call libusb_init failure
```
uuu 在**解析参数之前**就初始化 libusb，而本沙箱/CI **没有 USB 子系统** → 任何形态（`-h`/`-V`/`--version`/无参）
实测全部 abort（rc=134/‑6）。
→ 处置：**用 LD_PRELOAD 给 libusb 打桩**（`libusbstub.c` 只让 `libusb_init`/热插拔注册/设备枚举“成功且无设备”，
**不伪造任何设备**），此后跑**真实二进制**：`uuu -h` rc=0 且打印上游用法、`uuu -V` 打印 libuuu 版本横幅
⇒ 补全的功能级测试 **1/1（100%）**。原生的 rc=-6 只作为**具名平台限制**在消费者侧单独记 skip、**不计入通过**。

## 实测结果（本地 conan create）
```
[added tests] 产物 = <build>/Release/uuu/uuu（5720640 字节）
[added tests] ⓪ 原生（不打桩）`uuu -h` rc=-6：libc++abi: … std::runtime_error: Call libusb_init failure
[added tests] ① 打桩后 `uuu -h` rc=0 且打印上游用法 ✓（首行：uuu (Universal Update Utility) for nxp imx chips -- libuuu_1.5.243-0-g230f1b1）
[added tests] ② 打桩后 `uuu -V` 打印 libuuu 版本横幅 ✓
[ok]   产物齐备：bin/uuu 存在且可执行（5720640 字节）
[ok]   ELF 头自检：真 ELF64、machine=0xB7(AArch64) ✓
[skip] 原生运行 `uuu -h` 在本环境无法完成（rc=-6：无 USB 子系统）——单独记 skip，不计入通过
[ok]   打桩 libusb 后**真跑通**：`uuu -h` rc=0 且打印上游用法 ✓
[ok]   打桩后 `uuu -V` 真跑通：打印 libuuu 版本横幅 ✓
[ok]   无参调用有明确输出（rc=0）——非静默退出
[ok]   许可证随包：licenses/LICENSE 存在
[ok]   证据：bin/uuu sha256=29969ce5e91effd9…；python 3.12.9
checks=8 fails=0 skips=1
RESULT: PASS
```
