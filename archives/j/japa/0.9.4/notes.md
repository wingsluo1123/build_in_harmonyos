# japa 0.9.4 适配笔记

## 编译环境
- 构建系统: makefile（上游仅 `source/Makefile`，无 configure / cmake / meson 入口；tarball 顶层为 AUTHORS/COPYING/README/source/）
- 编译日期: 2026-10-13
- 编译器: clang/clang++，取 profile `tools.build:compiler_executables`（create5.log，profile 为仓内 `ci/conan/profiles/ohos-aarch64`，`-pr:h` 与 `-pr:b` 同给）
- 状态: built

## 编译步骤

1. `conan create archives/j/japa/0.9.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=japa --build=missing`
2. `build()`：`apply_conandata_patches` → 收集全部声明依赖的 `includedirs`/`libdirs` →
   `make -C source -j1 PREFIX=/ CXX=<profile 编译器> PCONFCFL="<-I. -DCLTHREADS_NO_PTHREAD_CANCEL + 各依赖 -I>" LDFLAGS="<各依赖 -L>" japa`
   （japa 源码平铺在 tarball 的 `source/` 子目录，与 jaaa 相同）
3. `package()`：`make -C source install PREFIX=/ DESTDIR=<package_folder>`（PREFIX=/ 使 `-DPREFIX` 烧 `/` 而非宿主 `/usr/local`，产物层断言 `artifact-no-host-prefix-leak` 全字节扫描兜底）
4. 上游无 check/test 目标（见下节），消费者测试放在 `test_package/`

## 上游测试申报（R51 三步法）

- tests/ 目录：无（tarball 仅 AUTHORS/COPYING/README/source/）
- check 目标：无（`make -n check` → No rule to make target 'check'；Makefile 仅 japa/install/uninstall/clean）
- 测试源文件：无（source/ 共 7 个 .cc + 6 个 .h + Makefile，无任何测试框架痕迹）
- 三项清点证据已写入 test_package/MANIFEST.yml 的 upstream_zero_evidence

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CXXFLAGS += -march=native` | 交叉工具链下以构建机 ISA 为准，宿主特性烧进 OHOS 产物 | 补丁摘掉（jaaa 同款，条目 DRAFT-genann-1.1.1-make-cflags-march-native-override 同族） |
| 2 | 上游 `CPPFLAGS += $(shell pkg-config --cflags freetype2)` 探测不可依赖 | 裸 make 构建不消费 Conan 元数据（jaaa 是 pkgconf，japa 是 pkg-config，同症状族 E468） | 补丁替换为 `$(PCONFCFL)` 注入槽，build() 注入 12 个依赖的 -I（保留上游自身 -DVERSION/-DPREFIX） |
| 3 | clthreads 在 OHOS 需 `CLTHREADS_NO_PTHREAD_CANCEL`（musl 无 pthread_cancel） | 该宏经 CMakeDeps 传递，裸 make 不消费 | build() 在 `settings.os == OHOS` 时拼进 PCONFCFL |
| 4 | 上游 install 规则用裸 `install` 命令 | OHOS PATH 无 install（toybox applet 仅 /bin/install） | 补丁引入 `INSTALL ?= /bin/install` |
| 5 | 构建主机无 X server、无 JACK/ALSA：X11 GUI + 音频分析器"跑得起来"不可达 | 平台无显示后端（E471），X11 侧消费者契约 E530 | 消费者测试三层（与 jaaa 同构）：产物层 4 条（AArch64/裸 soname/codesign 段数/无宿主前缀）+ 装载进程层 3 条（`japa -h` 横幅 Japa-0.9.4 + exit 1 语义 + 无参运行 `Can't open display` 签名且非 127/126）+ 能力层 3 条逐用例 SKIP 带原因 |
| 6 | 本机离线喂源码：backup source 报 "not found in remote backup" | conan backup 源要求 `<sha256>` 与 `<sha256>.json` 成对（caching_file_downloader.py:104-107），且 file:// scheme 无 connection adapter | 本地起 http.server 8732 服务 sha256 命名的源码包 + .json 元数据（references 指向官方 URL），download_urls 指向之 |

## 源码修改

`patches/0001-Makefile-portability.patch`（patch_type: portability），只动 `source/Makefile`：

1. 新增 `INSTALL ?= /bin/install`
2. `CPPFLAGS += $(shell pkg-config --cflags freetype2)` → `CPPFLAGS += $(PCONFCFL)`
3. 删除 `-march=native`
4. install 规则 `install -d/-m 755` → `$(INSTALL) -d/-m 755`

未改动任何 .cc/.h。

## 依赖版本

与 jaaa 0.9.2 同一闭包（X11 1.8.13 轨）：clxclient/3.9.2、clthreads/2.4.0（clxclient 钉 2.4.0）、libxft/2.3.8、libx11/1.8.13、xorgproto/2025.1、fontconfig/2.18.3、libxrender/0.9.12、freetype/2.14.3；音频后端 jack/1.9.22、zita-alsa-pcmi/0.6.1、alsa-lib/1.2.16；DSP fftw3f/3.3.10（单精度独立包名，非 fftw 包）。

## 验证结果

```bash
# conan create 全流程（create5.log）
JAPA_SMOKE_PASS load=2 process=1 skipped=3 failed=0   # RC=0
```
---

**编译结束**: 2026-10-13 14:40
**最终状态**: built
