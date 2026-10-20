# libbasicobjects 0.2.0 — OHOS 适配笔记

## 版本映射(重要)

| 项 | 值 |
|---|---|
| 任务/配方版本 | 0.2.0(分支 feat/libbasicobjects-0.2.0)|
| 上游源 | SSSD/ding-libs 0.6.2 官方发行包(2022-01-25)|
| 上游子库版本 | basicobjects 0.1.1(ding-libs 最后的独立实现)|
| soname | libbasicobjects.so.0(-version-info 1:0:1)|

上游版本拓扑调研结论:
- ding-libs ≤0.6.2:basicobjects 是伞形仓库中的独立 `lib_LTLIBRARIES`
  (version.m4 `BASICOBJECTS_VERSION_NUMBER`,0.6.2 = 0.1.1)。
- ding-libs 0.7.0(2026-03-03)及 master:basicobjects 源码并入
  libini_config 内部便利库,**不再独立出库**。
- 上游从未发布过 basicobjects 0.2.0;任务目录的 0.2.0 是平台任务标识,
  R37 空间无冲突(制品仓无任何 libbasicobjects 版本)。
- patch 0001 将 configure/version.m4 的子库版本对齐 0.2.0,使安装的
  basicobjects.pc `Version:` 与 conan ref 一致;soname 维持
  libbasicobjects.so.0(上游 ABI 未动)。

## 源选择

主源 = GitHub 官方 release asset `ding-libs-0.6.2.tar.gz`
(sha256 `e5f07f34…`,与官方 `.sha256sum` asset 核对一致):
带预生成 configure/aclocal.m4/Makefile.in/config.h.in,构建机无需
autotools 工具链。

备源 = codeload tag archive(sha256 `9068981a…`,与官方 asset 字节流
不同,且**无**预生成 configure):build() 检测 configure 缺失时用
`autoreconf -fiv` 兜底生成。

## OHOS 适配问题与对策

1. **config.guess 不识别 HarmonyOS**(2018-08-29 时间戳)
   → OHOS 时显式 `--build/--host=aarch64-unknown-linux-gnu`
   (config.sub 原生支持 aarch64,无需 patch)。

2. **伞形全量构建被 gettext 阻断**:path_utils.h 无条件
   `#include <libintl.h>` + `#define _(s) gettext(s)`,OHOS musl 无
   GNU gettext 实现 → `-Wint-conversion` 编译错误(知识库桶4 同源,
   rec 为 --disable-nls)。但 libbasicobjects 本体**零** gettext 依赖:
   → `--disable-nls` + 目标级构建 `make simplebuffer_ut`
   (automake 自动连带 libbasicobjects.la),完全不触碰 path_utils。

3. **config.status tmp 目录 umask 坑**(CI Worker HMDFS setgid +
   umask 077 → 组不可写,makefile fragments 引导失败)
   → patch 0002(a52dec 0.7.4 同款先例)。

4. **受限执行环境 execve 限制**(本机真机/沙箱;CI 老款 Worker 间歇):
   - shebang 脚本一律 `Permission denied` → configure 用 bash 显式解释;
     make 传 `SHELL=<abs bash>`。
   - automake `MKDIR_P=<srcdir>/build/install-sh`(shebang)→ make 传
     `MKDIR_P='<abs mkdir> -p'`。
   - libtool 生成的 simplebuffer_ut wrapper 是 /bin/sh 脚本 → 直接执行
     `.libs/simplebuffer_ut` 真 ELF。
   - conan Autotools helper 的 configure 调用经 `tools.gnu.env`…实际由
     recipe 的 `_ensure_configure`/make args 处理,不依赖 wrapper。

5. **shared 变体 UT 运行时库定位**:libtool 链接的 UT RUNPATH 指向
   `$prefix/lib`(= conan package_folder/lib,AutotoolsToolchain 默认
   prefix)→ build() 内先 `_deploy_package_layout()` 再跑 UT,UT 加载
   同批构建的 .so;本机验证 LD_LIBRARY_PATH 不可用的环境下仍正常。

6. **不做 `make install`**:伞形 install 目标会安装全部子库(未构建即
   失败)。手动部署:.libs 产物 → lib/,simplebuffer.h → include/,
   configure 生成的 basicobjects.pc(prefix 重写为
   `${pcfiledir}/../..`)→ lib/pkgconfig/,COPYING → licenses/。

## 上游测试

- 官方注册:`TESTS += simplebuffer_ut`(Makefile.am basicobjects 段),
  `make check` 的 basicobjects 条目。
- 语义:alloc → add_raw/add_cr/add_str → get_len/get_buf →(verbose 时
  write 到 fd 1)→ free,任一步出错 `return error`(非 0),全部成功
  exit 0。
- CI L1:build() 内执行真 ELF `simplebuffer_ut -v`,退出码即验收。
- test_package:vendored 上游 UT 源(链接安装库)复跑 + 消费者探针
  16 断言(全 API + 字节级 round-trip + 临时文件 IO 路径)。

## 本机验证记录(2026-10-16,真机 OHOS aarch64)

- 裸构建(static + shared 双变体):configure/make 全过,UT exit 0。
- conan create(static + shared):见提交后本地日志。
