# libxfce4util 4.20.0 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 自带 configure，无自举需求）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）
- conan: 2.29.1，profile ci/conan/profiles/ohos-aarch64
- 状态: published（候选，权威 CI 通过后交付）

## 编译步骤

1. `conan create archives/l/libxfce4util/4.20.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
2. generate(): PkgConfigDeps 物化 glib-2.0/gobject-2.0/gio-2.0 的 .pc，configure 参数注入 `PKG_CONFIG_PATH=<generators_folder>`
3. configure 选项: `--disable-nls --disable-gtk-doc --enable-introspection=no --enable-vala=no --disable-silent-rules`（shared 时加 `--enable-shared --disable-static`）
4. OHOS 专用处理:
   - build() 内对 libtool 替换 `hardcode_libdir_flag_spec` 置空（同 libgcrypt 1.12.2 先例，防 rpath 破坏 codesign）
   - package() 后对所有 ELF：patchelf --remove-rpath + 移除 .codesign 段 + binary-sign-tool selfSign
5. `make check` 在 build() 中显式执行——上游无测试套件，日志留 no-op 证据

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2022 版 config.sub 拒绝 aarch64-unknown-linux-ohos triple（rc=1） | 2022-01 发布的 config.sub 白名单无 ohos* / linux-ohos* | 补丁 0002：basic-OS 白名单加 ohos*、kernel-os 校验加 linux-ohos* |
| 2 | config.guess 无法识别 HarmonyOS 宿主 | tarball 内置 config.guess 无 *:HarmonyOS:*:* 分支 | 补丁 0001：新增 HarmonyOS case，按 uname -m 归一化输出 aarch64-unknown-linux-ohos |
| 3 | configure 临时目录创建失败（HMDFS） | autoconf 模板 `umask 077 && mktemp -d`，HMDFS 上 077 权限目录不可用（E011） | 补丁 0003：umask 077→022（mktemp 与 mkdir 两处） |
| 4 | NLS 潜在链接失败 | configure.ac 使用 AM_GNU_GETTEXT([external])，会拉 host libintl（E015/E027 同签名） | configure `--disable-nls`（同经验仓 xapp libintl 条目结论） |
| 5 | xfce4-kiosk-query 链接闭包隐式依赖 | 该工具 LDFLAGS 仅含 libxfce4util.la，glib libdir 经 .la dependency_libs 隐式传递，违反 lld 显式闭包定律（build-chain-pitfalls 共享库链接闭包节） | 配方 generate() 显式追加 `-L<glib libdir>`（AutotoolsToolchain extra_ldflags，env 快照前注入） |
| 6 | 消费者链接报 `undefined reference due to --no-allow-shlib-undefined: g_libintl_textdomain`（CI run3 实测） | `--disable-nls` 下 xfce-i18n.c/libxfce4util-private.c 的 textdomain 调用仍无守卫，而 glib 包内 proxy-libintl 的 libintl.h 把它们重绑为 g_libintl_*，唯一供给 DSO 在 glib 包 lib/ 内、消费者链接行定位不到 | 补丁 0004：给两处 i18n 调用加 `#ifdef ENABLE_NLS` 守卫（NLS 关闭时按上游语义 no-op），产物不再携带 UNDEF g_libintl_* |
| 7 | 尝试以绝对路径注入 libintl DSO 反致 configure 报 `cannot run C compiled programs`（CI run4 实测） | 绝对路径 .so 进 LDFLAGS 会进入每个 conftest 链接，conftest 运行时按 SONAME 找不到 libintl.so.8（error 77） | 放弃该路径，改用 0004 源码守卫（对下游消费者才是完备闭包） |
| 8 | test_package 报 `missing installed xfce4-kiosk-query`（CI run6 实测）：断言在 `<pkg>/sbin/` 找不到工具 | Conan 2 `AutotoolsToolchain` 默认注入 `--sbindir=${prefix}/bin`（bin 展平；知识条目 E2167/E545 佐证该工具链无条件注入全部 GNU 目录参数），libtool install 日志证实落点为 `p//bin/xfce4-kiosk-query`，包内真实路径是 bin/ 而非上游语义的 sbin/ | 以事实为准对齐配方声明：`cpp_info.bindirs=["bin"]`、test_package 断言改查 `bin/`；不强行改写 `--sbindir`（与工具链默认行为对抗无收益，且 CI 安装面冒烟按 bin/ 探测） |

## 源码修改

三个补丁全部为平台差异最小修复（均为 portability 类）：

- `patches/0001-config.guess.patch`：config.guess 增加 HarmonyOS 宿主识别
- `patches/0002-config.sub.patch`：config.sub 接受 ohos kernel-os 组合（本库 2022 版 config.sub 必需，否则 conan 传入的 --host triple 直接被拒）
- `patches/0003-configure.patch`：configure mktemp/mkdir umask 077→022（E011）
- `patches/0004-disable-nls-i18n-guards.patch`：xfce-i18n.c/libxfce4util-private.c 的 i18n 调用加 ENABLE_NLS 守卫（--disable-nls 下消除 g_libintl_* UNDEF，E015/E027 家族，xapp-2.8.9 同签名）

## 依赖版本

- glib/2.84.0.1（本仓最广泛部署的已发布基线，184 个配方同版；configure.ac 要求 glib-2.0/gobject-2.0/gio-2.0 >= 2.72.0）

## 验证结果

权威 CI（ci/conan/build_and_test.sh，profile ohos-aarch64）：

- L0/L1/L2/L4/L5 各层结果见 CI 日志与 ci-metadata.json
- test_package 自建用例（上游无测试套件，NO_UPSTREAM_TESTS 申报见 test_package/MANIFEST.yml）：
  - `version`：xfce_version_string() == 4.20.0
  - `ohos-guard`（OHOS 特有）：__OHOS__ 分支实际生效 + 运行时内核身份（HarmonyOS/aarch64）与补丁 0001 适配的平台事实一致
  - `fileutils-roundtrip`：xfce_mkdirhier + xfce_rc INI 写/关/重开/读全链路在 OHOS 文件系统上往返
  - 安装面：lib/pkgconfig/libxfce4util-1.0.pc Version 4.20.0；bin/xfce4-kiosk-query -v 在 OHOS 动态链接器下真实运行
- `make check`：check-recursive 无 TESTS，no-op（证据在 CI 日志 build 段）

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libxfce4util.so.7.0.0（+ .so.7/.so 链） | 主库，verinfo 7:0:0 |
| lib/pkgconfig/libxfce4util-1.0.pc | pkg-config 模块（Requires: glib-2.0） |
| include/xfce4/libxfce4util/*.h | 头文件 |
| bin/xfce4-kiosk-query | kiosk 能力查询 CLI（上游 sbin_PROGRAMS，conan 包内被展平到 bin/，见问题 #8） |
| licenses/COPYING | LGPL-2.0 |

## 注意事项

- 下游（xfconf 等）以 `XDT_CHECK_PACKAGE([LIBXFCE4UTIL], [libxfce4util-1.0], ...)` 消费，conan 侧 pkg_config_name 已对齐为 libxfce4util-1.0，cmake target 为 libxfce4util::libxfce4util
- L2 冒烟对 xfce4-kiosk-query 为非阻塞 warn：该工具仅支持 `-h/-v` 短选项，CI 的 `--version/--help` 长选项探测落 usage(TRUE) 退出非零；test_package 已用 `-v` 完成真实冒烟
- xfce4-kiosk-query 上游声明 sbin_PROGRAMS，但 conan 包内 AutotoolsToolchain 把 sbindir 展平到 bin/（run6 实证 + E2167/E545），包内消费按 `bin/xfce4-kiosk-query` 定位
- 补丁直接改 configure/config.guess/config.sub，不触碰 configure.ac/Makefile.am，automake mtime 重生成坑（经验仓 enchant-2.8.2 条目）不适用；conan patch 后 mtime 晚于模板文件，顺序安全
