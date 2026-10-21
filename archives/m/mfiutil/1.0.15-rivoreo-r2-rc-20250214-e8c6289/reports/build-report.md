# mfiutil 1.0.15-rivoreo-r2-rc-20250214-e8c6289 - 编译报告

> **编译日期**: 2026-10-17
> **编译环境**: WSL 原生 ext4（/root/ohpcd-work），交叉编译至 OpenHarmony PC aarch64
> **编译器**: clang 15.0.7（`/opt/lpk-fixed/clang`，target `aarch64-unknown-linux-ohos`）
> **C 库**: OHOS libc（动态链接 `libc.so`，interpreter `/lib/ld-linux-aarch64.so.1`）

## 源码

- 上游官方源码库：Rivoreo Gitiles <https://src.rivoreo.one/mfiutil>，版本串内嵌提交
  `e8c62898089593cd039b7d0360e030f04f9bfb45`（2025-02-14）。
- 官方 Gitiles 归档 `+archive/e8c6289.tar.gz` HTTP 200，但每次请求即时生成
  （gzip 头带时间戳），两次下载 sha256 不同（实测 `8a6e8eb5…` vs `860dcc4e…`），
  无法钉校验和。
- 取源改用 Debian 官方归档（deb.debian.org 官方 CDN，非镜像站）同一提交 orig tarball：
  `https://deb.debian.org/debian/pool/main/m/mfiutil/mfiutil_1.0.15-rivoreo-r2~rc-20250214-e8c6289.orig.tar.bz2`
  sha256 `21f303c6a467c45a0f32f48eeb5118e641850b23d42f8352b93e0c75a8bba63a`
  （与同目录 PGP 签名 .dsc 的 Checksums-Sha256 逐字一致；与上游 Gitiles 树
  `diff -r` 完全相同，仅少一个 .gitignore）。归档扁平结构。

## 编译配置

```bash
# 解包（扁平，无顶层目录）
mkdir -p /root/ohpcd-work/build/mfiutil-1.0.15-rivoreo-r2-rc-20250214-e8c6289
cd /root/ohpcd-work/build/mfiutil-1.0.15-rivoreo-r2-rc-20250214-e8c6289
tar xjf mfiutil_1.0.15-rivoreo-r2~rc-20250214-e8c6289.orig.tar.bz2

# 交叉编译（OHOS clang；上游 Makefile 硬编码 CC:=gcc，命令行赋值覆盖；
# CFLAGS 保持上游默认 -std=gnu99 -Wall -Wno-unused-value -Os -I include）
make CC=/opt/lpk-fixed/clang -j1
```

## 编译结果

- 退出码 0。8 条上游既有 warning（packed 成员取址、`__start/__stop_set_mfiutil_ctrlprop`
  STB_WEAK 绑定等），非错误，未改动源码。
- 产物：`mfiutil` — `ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
  interpreter /lib/ld-linux-aarch64.so.1`
- 无第三方库依赖（NEEDED 仅 `libc.so`），无补丁。

## Conan 打包（CI 等价路径）

```bash
conan create . \
  -pr:h /root/.conan2/profiles/ohos-aarch64-wsl \
  -pr:b /root/.conan2/profiles/ohos-aarch64-wsl \
  --build=missing
```

- package_id `6b129b068851896169fae42d399fa922d239ce8a`，
  包内布局 `usr/sbin/mfiutil` + `usr/share/man/man8/mfiutil.8`
  （走上游 `make install DESTDIR=… PREFIX=/usr`）。
- test_package 6/6 通过（见 test-report.md）。
