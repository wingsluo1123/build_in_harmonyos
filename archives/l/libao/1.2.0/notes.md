# libao 1.2.0 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 自带预生成 `configure`，无需 autoreconf）
- 编译日期: 2026-10-09
- 编译器: clang 15.0.4 (`/data/service/hnp/bin/clang`), clang++
- 目标: OHOS aarch64（HarmonyOS PC / oss=OHOS 6.0）
- 源码: `https://downloads.xiph.org/releases/ao/libao-1.2.0.tar.gz`
  （sha256 `03ad231ad1f9d64b52474392d63c31197b0bc7bd416e58b1c10a329a5ed89caf`，R39 官方源）

## 编译步骤
1. 解压官方 tarball（`strip_root`），应用 3 个补丁（config.guess / config.sub / configure）
2. VPATH 构建：`CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
   TMPDIR=$HOME/tmp sh <src>/configure --prefix=...` → `make -j4`
3. configure 探测结果（R1：未加任何手工 disable 参数）：
   - 保留文件写入驱动：**wav / raw / au / null = yes**（无音频设备也可功能验证）
   - live 后端全部自动关闭：alsa / pulse / esd / nas / arts / sndio / sun / irix / macosx / roar = no
   - OSS 插件 = yes（平台探测到 OSS 头；与既有 1.2.2 归档行为一致，`liboss.so` 仅依赖 libc）
4. `make check`：上游无测试（N=0，见 `test_package/MANIFEST.yml` 的 R51 清点）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`（uname -s = HarmonyOS） | GNU config.guess 2012-12-29 无 HarmonyOS 分支（E007） | 补丁 0001：新增 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`（无 `__OHOS__` 宏，PF5 合规） |
| 2 | `config.sub: system 'ohos' not recognized` | 同上（E007） | 补丁 0002：`maybe_os` 表 + OS 列表接受 `linux-ohos` 三元组 |
| 3 | configure 生成 config.status 阶段 `Permission denied`（confXXXXXX 临时目录） | HMDFS UID 映射 + `umask 077`（E011） | 补丁 0003：`umask 077` → `umask 000`（同 acl 先例） |
| 4 | conan create 时 `configure: error: working directory cannot be determined` + 大量 `getcwd` 风暴 | profile buildenv 注入 `CONFIG_SHELL=<hnp bash>`；autoconf **2.69** 生成的 configure 无条件 re-exec `$CONFIG_SHELL`，该 bash 在 HMDFS 上 getcwd 失败（知识草稿 DRAFT-autoconf269 / DRAFT-6487；classads/cdck 先例） | 配方 build() 内手动运行 configure：`unset CONFIG_SHELL; CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh configure <toolchain_args>`（unset 而非置空；configure_args 由 `load_toolchain_args` 保持） |

## 源码修改（全部经 `ohc-run.py refresh-patch` 生成，R3）
- `0001-config.guess.patch`（+9）：HarmonyOS 系统识别（对非 OHOS 平台零影响）
- `0002-config.sub.patch`（+2/-2）：linux-ohos 三元组支持
- `0003-configure.patch`（+2/-2）：E011 umask 修复

## 依赖版本
无 Conan 依赖；仅系统 libc（readelf DT_NEEDED = `libc.so`）。

## 验证结果
- 探索编译：configure rc=0，make rc=0（21 warnings 均无害：上游 pointer-sign + `-O20` 回退提示），make check rc=0（no-op）
- 设备冒烟（探索阶段）：`ao_initialize` + `ao_driver_id("wav"/"null")` + `ao_open_file` 写 1s 440Hz 正弦波 →
  88268 字节 = 68 + 44100×2，RIFF/WAVE 校验通过；消费者 ELF：aarch64 + musl 解释器 + `.codesign` + NEEDED `libao.so.4`
- conan-verify：G0–G4 + L2/L4/L5 结果见 `reports/conan-verify-report.md`

## 注意事项
- wav 驱动头为 WAVE_FORMAT_EXTENSIBLE（68 字节），下游断言文件尺寸时按 `68 + 2*bytes` 计算
- R26：系统无同名 `libao`，默认动态（`shared=True`）；如需静态：`-o libao/*:shared=False`（generate 会加 `--disable-shared --enable-static`）
- 打包时删除 `lib/**/*.la`（libtool 绝对路径陷阱，libidn2 先例）
- 执行路径：环境中的 HNP bash 无法 exec 用户 ELF（rc=126 `cannot execute binary file`）→ test_package 采用**直接 exec**（与真实消费者同路径）；若沙箱拒绝执行则降级到 fail-closed ELF 断言，绝不静默跳过
---

**编译结束**: 2026-10-09 01:00
**最终状态**: published
