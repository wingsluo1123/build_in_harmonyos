# libx11 1.8.13.2 适配笔记

## 任务目标
暴露 `libX11-xcb.so`（`XGetXCBConnection` / `XSetEventQueueOwner`）给下游消费。

## 与基座 1.8.13.1 的区别
- 版本号: 1.8.13.1 → 1.8.13.2（R37: 同版本适配修复递增 N）
- `package_info()`: `libs = ["X11"]` → `libs = ["X11", "X11-xcb"]`
- 依赖新增 libxcb：上游 configure.ac 的 `X11_REQUIRES` 固定 `xcb >= 1.11.1`，Xlib-xcb 是**无条件构建**（`AC_CONFIG_FILES` 内含 `x11-xcb.pc`），无 `AC_ARG_ENABLE(xcb)`；因此不需要也不存在 `--enable-xcb` 开关（该选项在 1.8.13 configure 中为 unrecognized）
- `package()` 新增 `_require_xlib_xcb()` 硬校验：包内无 `libX11-xcb.so*` 直接抛错，避免 package_info 声明与实际产物静默不一致
- 依赖更新: libxau 1.0.11→1.0.12, libxcb 1.17.0→1.17.0.1（与 1.8.13.1 基座对齐）
- 新增依赖: xtrans/1.4.0, xcb-proto/1.17.0（与基座对齐）

## 编译环境
- 构建系统: autotools
- 编译器: clang/clang++ (15.0.4 OHOS toolchain)

## 编译步骤

1. 下载源码 tarball: libX11-1.8.13.tar.xz (sha256: 69606f485c2c07c14ef64f75b7bb326d48587af33795d9ab3e607c0b5f94f11c)
2. 解压并应用 OHOS autotools 修复 (同基座)
3. 配置:
   ```
   ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
     --without-xmlto --without-fop --without-xsltproc \
     --enable-shared --disable-static
   ```
4. 编译 + 上游测试: `make && make check`
5. 包内产物: libX11.so, libX11-xcb.so, Xlib-xcb.h, x11-xcb.pc

## 验证结果

```bash
conan create archives/l/libx11/1.8.13.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default
# Package 'cae7d429...' created, exit 0
```
---

**编译结束**: 2026-10-18 04:45
**最终状态**: built
