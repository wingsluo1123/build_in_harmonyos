# libgdm 50.1 适配笔记

## 编译环境
- 构建系统: meson (>= 0.57，实际使用 meson 1.11.1)
- 编译日期: 2026-10-02
- 编译器: clang 15.0.4 (OHOS SDK llvm) / clang++
- 平台: HarmonyOS PC aarch64-ohos (native build，非 cross)
- 状态: published

## 编译步骤

源码：GNOME gdm 50.1 官方 release tarball（download.gnome.org + NJU 权威镜像）
（sha256 = 770159373512192410f412b5d0c4678ec1573f1ae4b39c81fe75861fe8890174）。

Conan 配方（conanfile.py）在 generate() 中：
1. `PkgConfigDeps` 生成各依赖 .pc（glib/gobject/gio/json-glib/accountsservice/
   audit/gudev-1.0/pam/check 等）。
2. 合成缺失 .pc：
   - `gio-unix-2.0.pc`（复制 gio-2.0.pc 改名，glib 配方无该组件）
   - `libsystemd.pc`（systemd 配方只生成 systemd.pc，包内也无 .pc）
   - `polkit-gobject-1.pc`（从 polkit 包内复制并把裸 `prefix=/` 改写为真实包目录）
3. `MesonToolchain` 设置项目选项：
   `-Dintrospection=disabled -Dplymouth=disabled -Dselinux=disabled
   -Dsystemd-journal=false -Dsystemdsystemunitdir=no -Dx11-support=false
   -Dlibaudit=enabled -Dlogind-provider=systemd -Ddefault_library=shared`
4. 把 linux-pam 包 lib/include 注入 c_link_args/c_args（`cc.find_library('pam')`
   OHOS sysroot 无 libpam）。
5. 向 meson native 文件注入 ar/ranlib/pkg-config；构建时把所有依赖 bin 目录
   加入 PATH、lib 目录加入 LD_LIBRARY_PATH（meson 的 gnome 模块需要
   gdbus-codegen/glib-mkenums/glib-compile-schemas，data/dconf custom_target
   需要 dconf 二进制）。

然后：
- `meson configure` → `meson build`（ninja）
- `meson test`（上游测试 m-common，见“验证结果”）
- `meson install` → 对包内 ELF 重新 binary-sign-tool 签名（install 改写了
  RPATH 会使 .codesign 失效）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson configure 报 `dependency('gio-unix-2.0')` 找不到 | glib conan 配方只有 gio-2.0 组件，无 gio-unix-2.0.pc | generate() 复制 gio-2.0.pc 合成 gio-unix-2.0.pc |
| 2 | daemon 链接报 lckpwdf/ulckpwdf undefined | OHOS musl libc.so 不导出该 API，SDK sysroot libcrypt.a 为空 | 新增 daemon/gdm-lckpwdf-compat.c 用 flock(2) 实现（patch 0003/0004） |
| 3 | meson configure `dependency('libsystemd')` 找不到 | systemd/261.1 配方只生成 systemd.pc，包内无 libsystemd.pc | generate() 从 systemd 包目录合成 libsystemd.pc |
| 4 | meson configure `dependency('polkit-gobject-1')` 找不到 | polkit/127 配方无 cpp_info 组件，PkgConfigDeps 只生成 polkit.pc；包内 .pc 的 `prefix=/` 裸路径 | 复制包内 polkit-gobject-1.pc 并把 prefix 改写为真实包目录 |
| 5 | `cc.find_library('pam')` 失败 | OHOS sysroot 无 libpam | 把 linux-pam 包 lib 目录注入 MesonToolchain c_link_args |
| 6 | data/dconf custom_target `Program dconf not found` | 构建期需要执行 dconf 二进制 | requirements 加 dconf/0.40.0.1（visible=False），构建时把其 bin 加入 PATH |
| 7 | libgdm/meson.build 无条件 generate_gir 导致缺 g-ir-scanner | OHOS 无 gobject-introspection 扫描器 | meson_options.txt 新增 introspection 选项并条件编译（patch 0001/0002） |
| 8 | meson configure 报 `Program 'itstool' not found`（docs/meson.build yelp） | yelp 模块强依赖 itstool，conan 构建环境无该工具 | patch 0005：仅当 find_program('itstool') 找到时才构建帮助页 |
| 9 | meson 构建期执行 glib-compile-schemas 报 `Operation not permitted`（code=126） | glib 包内 C 工具在 worker 上 .codesign 无效（需重新签名） | 配方把 glib 的 ELF 工具复制到 build 目录并重新 binary-sign-tool 签名，.pc 的 *_tool 变量指向签名副本 |

## 源码修改

| 补丁文件 | 内容 |
|----------|------|
| patches/0001-introspection-meson-option.patch | meson_options.txt 新增 `introspection` feature 选项（默认 disabled） |
| patches/0002-gir-conditional.patch | libgdm/meson.build 的 gnome.generate_gir 包进 `if get_option('introspection').enabled()` |
| patches/0003-lckpwdf-compat-source.patch | daemon/meson.build 的 gdm daemon 源列表加入 gdm-lckpwdf-compat.c |
| patches/0004-gdm-lckpwdf-compat.c.patch | 新增 daemon/gdm-lckpwdf-compat.c（flock(2) 实现 lckpwdf/ulckpwdf） |
| patches/0005-docs-itstool-optional.patch | docs/meson.build 仅在 itstool 可用时构建 gnome.yelp 帮助页（文档对 libgdm 库非必需） |

## 依赖版本

| 依赖 | 版本 |
|------|------|
|  glib (glib/gobject/gio/gio-unix) | 2.84.0.1 |
| systemd (libsystemd) | 261.1 |
| json-glib | 1.10.6.1 |
| accountsservice | 26.27.3 |
| polkit | 127 |
| libaudit (audit) | 2.7.4 |
| libgudev (gudev-1.0) | 238 |
| linux-pam | 1.7.2 |
| check | 0.15.2 |
| dconf | 0.40.0.1 |

## 验证结果

```bash
# work 目录探索构建（上游测试）
meson test -C build-ohos
# Log of Meson test suite run on 2026-10-02T17:15:24
# test:         gdm:m-common
# result:       exit status 0
# 100%: Checks: 1, Failures: 0, Errors: 0
# Ok: 1 / Fail: 0

# Conan 配方验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libgdm 50.1 --project-dir /storage/Users/currentUser/runner/build_in_harmonyos
# → G0-G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 构建配方（GPL-2.0-or-later，libgdm 客户端库） |
| conandata.yml | 官方源码 URL + sha256 + 5 个补丁声明 |
| test_package/ | 真实编译链接 libgdm 的消费者冒烟测试（PkgConfigDeps + gdm.pc） |
| patches/ | 5 个 OHOS 适配补丁（git-style，patch_ng strip=0 可应用） |
| reports/ | conan-verify 报告 + conan-create 日志 |

## 注意事项

- gdm 顶层 meson.build 没有跳过子目录的选项：构建整个项目树（daemon、utils、
  pam_gdm、po、data、docs），所以 daemon 侧依赖（json-glib/accountsservice/
  polkit/libaudit/libgudev/linux-pam/dconf）都必须声明；它们只用 visible=False，
  不影响 libgdm 消费者 cpp_info。
- libgdm.so 是 `library('gdm')`，soname libgdm.so.1；pkg-config 文件名为 `gdm`。
- 包内还包含 gdm 守护进程二进制（sbin/gdm、libexec/gdm-session-worker、
  gdm-wayland-session、bin/gdm-config 等）与 pam_gdm.so、GSettings schema。
- OHOS /tmp 只读：配方把 TMPDIR 指到 build_folder/tmp。
- 上游测试仅有 1 个可构建用例 m-common（tests/meson.build），已通过；
  s-common 是被 m-common 引用的公共头/辅助（非独立测试）。

## 结束标记

**最终状态**: 编译结束，conan create 成功，G0-G4 门禁通过，上游测试 m-common 1/1（100%）通过，test_package 冒烟测试通过。COMPLETED
