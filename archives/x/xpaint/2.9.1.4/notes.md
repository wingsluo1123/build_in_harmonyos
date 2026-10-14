# xpaint 2.9.1.4 适配笔记

## 编译环境
- 构建系统: makefile（Imake 体系手工提取，E546）
- 编译日期: 2026-10-05
- 编译器: clang 15（OHOS aarch64，ohos-aarch64 profile）
- 状态: published（conan-verify G0-G4/L2/L4/L5 全过；W3 本地 CI 模拟 Success 1/1）

## 编译步骤

conan 驱动（配方 archives/x/xpaint/2.9.1.4）：

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify xpaint 2.9.1.4
# conan create ... --build=missing --user=ohpcd --channel=stable
```

上游 ./configure 内调 xmkmf（OHOS 无 imake 工具链），配方完全绕开 Imake 体系：
三层 Imakefile（根/rw/xaw3dxft）手工提取编译单元，生成 GNUmakefile 编译；
生成物（Xaw3dP.h、laygram/laylex、XPaint.ad.h、messages.h 等）在 build() 内
用 Python/subprocess 预生成。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xmkmf: inaccessible or not found | Imake 体系依赖 X11 开发树（E546） | 手工提取编译单元，配方内 GNUmakefile |
| 2 | libx11/zlib/fontconfig 版本冲突 | 下游包钉不同版本 | override 统一（libxmuu 同款修法） |
| 3 | xaw_incdir/Form.h not found | 上游 configure 建 symlink，源码以 xaw_incdir/ 前缀包含 | build() 内 Python os.symlink（R5：先删后建） |
| 4 | Xaw3dP.h not found | Xaw3dP.h.sed 需 sed 展开，conan run PATH 无 sed | Python 逐行 XCOMM→# 转换预生成 |
| 5 | laygram.c 缺失/bison 输出名不符 | bison 3.x `-b` 输出 *.tab.c | `-o laygram.c -d` 显式命名 + yy→LayYY 改名 |
| 6 | XPaint.ad.h / messages.h 缺失 | 上游由 substads/preproc 宿主工具生成 | 配方内编译宿主工具并按 Imakefile 规则运行（host==target） |
| 7 | undeclared identifier 'vi' | -DEDITOR 引号被 make/shell 剥离 | defines 内 \\" 转义 |
| 8 | struct imageprocessinfo incomplete | image.h 的 #ifdef _XLIB_H_ 守卫与 conan 包 Xlib.h 的 _X11_XLIB_H_ 不匹配 | 主程序 CFLAGS 加 -D_XLIB_H_；rw/ 用 -include X11/Xlib.h |
| 9 | 'bool' 参数名冲突 | misc.h 原型参数与 stdbool typedef 撞名（0003 补丁） | 改名 boolval（R8 合规，无平台宏） |
| 10 | fractalFillPopup 未声明 | 漏掉上游 Local.config 的 EXTRA_DEFINES | 补 -DERRORBEEP -DFEATURE_FRACTAL |
| 11 | libXft.so.2 运行期 Permission denied | HMDFS 对该单文件 mmap(EXEC) 拒载（E524 家族，dlopen 实证；同区 libXmu/libXt/libX11 可载） | 静态桩注入：扫描未定义 Xft* 符号生成 stub（返回 NULL），二进制无 libXft DT_NEEDED；平台限制已在 manifest/test-report 如实申报 |
| 12 | 无显示环境测试退出 | XtOpenApplication 在选项解析前开显示 | 测试接受 usage 横幅或 "Can't open display" 双分支（均证明二进制真实执行） |

## 依赖版本

- xorgproto/2025.1, libx11/1.8.13(override), libxext/6.4.0.1, libxt/1.3.1, libxmu/1.3.1.1
- libxpm/3.5.17, libpng/1.6.58, zlib/1.3.1.1(override), libjpeg/10, libtiff/4.7.0
- libxft/2.3.8, fontconfig/2.18.1(override), freetype/2.14.3
- tool_requires: bison/2.7, flex/2.6.4

## 上游测试清点（R51）

- tarball 无 tests/ 目录，Imakefile 无 check 目标（Imake 体系无测试设施）
- rw/ 仅格式读写器源码 → upstream_tests: []（MANIFEST.yml 已申报清点证据）

## 验证结果

- conan-verify: G0-G4 + L2/L4/L5 全部 PASS
- W3 本地 CI 模拟: Success 1/1（100%）
- test_package: 消费者测试 3/3（headless 真实执行）

## 平台限制（如实申报）

libXft 动态加载被 HMDFS 拒绝（E524 家族，跨版本/位置/拷贝方式复现），
静态桩规避后 GUI 字体渲染路径返回 NULL；headless 测试不受影响，
画布场景字体回退行为受限。非配方面可修复，已留证据链于 conanfile.py 注释。

---

**编译结束**: 2026-10-05 23:10
**最终状态**: published
