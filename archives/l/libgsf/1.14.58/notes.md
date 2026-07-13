# libgsf 1.14.58 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码并解压
2. 应用补丁（如有）
3. 创建 gtk-doc.make 和 gtk-doc.m4 stub（避免 gtk-doc 依赖）
4. `autoreconf -fi -I m4`（生成 configure）
5. 修复 configure 中 umask 077→022（E011: HMDFS 权限问题）
6. `./configure --enable-static --disable-shared --disable-introspection --without-bz2 --without-gdk-pixbuf`
7. `make -j$(nproc)`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gtk-doc 依赖缺失 | 上游依赖 gtk-doc 但 OHOS 无此包 | 创建 gtk-doc.make 和 gtk-doc.m4 stub |
| 2 | configure 临时目录不可写 | HMDFS umask 077 (E011) | configure 中 umask 077→022 |
| 3 | /tmp 只读 | E002: OHOS /tmp 只读 | TMPDIR=~/tmp |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.84.0 | @ohpcd/stable (PR 待合并) |
| libxml2 | 2.15.3 | @ohpcd/stable (PR 待合并) |

## 验证结果

```
conan-verify 8/8 门禁通过 (G0-G4, L2/L4/L5)
test_package: gsf_init()/gsf_shutdown() smoke test PASS
```

## 注意事项

- 依赖 glib 和 libxml2 的 conan 包需先 upload 到 ohpcd remote
- libgsf 非系统同名库 (R26)，使用 --enable-static --disable-shared 静态链接
- 被依赖方: msitools 0.106 (#1789)
---

**编译结束**: 2026-07-06 13:40
**最终状态**: built
