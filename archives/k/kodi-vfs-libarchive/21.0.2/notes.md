# kodi-vfs-libarchive 21.0.2 HarmonyOS PC 移植说明

## 版本与源码

- 上游项目：<https://github.com/xbmc/vfs.libarchive>
- 官方标签：`21.0.2-Omega`（commit `089fb08587d534b2b709757eb389560781abd7f6`）
- 源码包 SHA-256：`aab35cb6b03191609a7e97df02f2f102659c12e414f7b95595f9bb2047554daf`
- 许可证：`LICENSE.md` 为 GPLv2 全文，`vfs.libarchive/addon.xml.in` 声明
  `GPL-2.0-or-later` → 配方 license 字段取 `GPL-2.0-or-later`
- 上游源码补丁：无（`patches: {}`）

### 命名消歧

"kodi-vfs-libarchive" = xbmc VFS 插件家族名（vfs.*）+ 项目名 libarchive。
上游 project id `vfs.libarchive`（addon.xml `id`），tag `21.0.2-Omega`，
Kodi 的 `archive://` 协议只读 VFS 插件（7z/tar/tar.gz/tar.bz2/tar.xz/zip/
gz/bz2/xz 浏览+读取；多卷 RAR 发现逻辑在源码内，正式 .rar 支持归
vfs.rar）。记录于 conandata/notes，交付 push gate 提请确认。

## 依赖与版本映射

| 上游 depends/common pin | ohpcd registry conan 配方 | 本包 require |
|---|---|---|
| libarchive 3.4.3（静态并入插件） | 3.7.4 / 3.7.7 / 3.8.7 | `libarchive/3.7.7` |

- 上游 REQUIRED 的 lz4/lzo2/openssl/liblzma/bzip2/zlib 全部是它**静态捆绑
  libarchive**（depends/common/libarchive，`-DBUILD_SHARED_LIBS=0`、
  `ENABLE_TEST=0`、`ENABLE_ZSTD=0` 等）的闭包，插件源码
  （src/ArchiveFile.cpp 单翻译单元）只 include `kodi/*` 与
  `archive.h`/`archive_entry.h`，无上述库直接调用 → 走 registry 共享
  libarchive 后全部无需提供。
- 选 3.7.7 而非 3.8.7：3.7.7 为 manifest `status: published` 的最新已发布
  版本，且其传递闭包（zlib/1.3.1.1、bzip2/1.0.8、xz/5.6.2、zstd/1.5.7）
  与 libarchive.so 吸收形态已在库内核验（zlib/bzip2/xz 静态吸收，
  zstd 留动态 NEEDED）；libarchive 公共 API 稳定，插件仅用
  archive_open/read/seek + entry 迭代等稳定面。
- registry libarchive 配方为共享库形态，插件模块保留对 `libarchive.so`
  的 DT_NEEDED（与 Kodi 发行版链接系统 libarchive 的部署形态一致）；
  test_package 运行时显式前置 libarchive/zstd 包 libdirs 到
  `LD_LIBRARY_PATH` 保证 dlopen 解析。
- kodi 头：无独立 registry 配方，经 conandata `sources.sdk` 从
  xbmc 21.3-Omega tarball 选择性提取（仅 `xbmc/addons/kodi-dev-kit/include`
  子树），与 kodi-tools/21.3、kodi-addon-screensaver/21.0.2、
  kodi-addon-imagedecoder/21.0.2 消费源一致。headers-only
  （AddonBase.h 全内联），模块不链接 libkodi。

## Conan 适配

- 上游 CMakeLists 是宿主 SDK 式（`find_package(Kodi REQUIRED)` +
  `build_addon()`，随 kodi-addon-dev 发行）；registry 无 kodi 包 → 按
  DRAFT-KODI01 模式：`recipe-cmake/` 自备构建入口（经
  `build_script_folder` 消费），MODULE 目标 + `PREFIX ""` 产物
  `vfs.libarchive.so`（addon.xml `library_@PLATFORM@` 的
  `@LIBRARY_FILENAME@` 期望名），`cxx_std_17`；VFS 插件无 GL/EGL 渲染
  路径，无需 HAS_GLES/GLESv3/EGL。
- 上游顶层 `-DLIBARCHIVE_STATIC -D_CRT_NONSTDC_NO_DEPRECATE` 仅影响
  Windows declspec/弃用告警分支，OHOS/clang 无语义，入口不复定义
  （注释注明）。
- **链接闭包显式化**：模块显式 `target_link_libraries(... libarchive::archive)`
  产生显式 DT_NEEDED——musl dlopen 只对插件自身 DT_NEEDED 闭包解析
  （E004 BIND_NOW + 经验仓 lcmaps-plugins-basic 条目）；zstd 作为
  libarchive.so 的动态 NEEDED 由运行期 LD_LIBRARY_PATH 前置兜底。
- **不定义** `BUILD_KODI_ADDON`/`ADDON_*_USED`（DRAFT-KODI01 禁止项：
  浅文本扫描检不出实例 API USED 宏，缺宏会让 `kodi/versions.h` 版本
  switch 缺 VFS case，静默错版本）。
- OHOS CMake：`CMAKE_SYSTEM_NAME=Linux`（E092，kodi-platform/
  imagedecoder 先例固定写法）。

## 上游测试

`NO_UPSTREAM_TESTS`（discovery 证据完整，2026-10-02 对实际解包源码复核）：

- 全树 `find -iname '*test*'` 唯一命中
  `depends/common/lzo2/01-disable-tests.patch`（上游依赖包的补丁文件名，
  非测试套件）；
- `CMakeLists.txt` 无 `enable_testing`/`add_test`/`ctest`（grep 零命中）；
- 上游 CI（`.github/workflows/build.yml` 名为 "Build and run tests" 实际
  仅构建，另有 .travis.yml/appveyor.yml/azure-pipelines.yml/Jenkinsfile
  同型）无测试执行步骤。

test_package 为消费者侧真实检查：dlopen 打包产物（musl 下 dlopen 成功
即证明显式 DT_NEEDED libarchive 闭包完整）、dlsym `ADDON_Create`/
`ADDON_GetTypeVersion`/`ADDON_GetTypeMinVersion` 三入口，实际调用
`ADDON_GetTypeVersion(110)`/`MinVersion` 断言 VFS 实例 API
`3.0.1`/`3.0.1`（xbmc 21.3-Omega SDK `kodi/versions.h` L165–166/L242
口径），并直接链接 libarchive 闭包做进程内功能冒烟（`archive_version_number()==3007007`、版本串前缀 `libarchive`、`archive_read_new/free`
往返，9 项断言）。headless 无 Kodi 宿主，archive:// 的 Open/Read/Seek
主功能由宿主回调驱动（CInstanceVFS），无法在无宿主环境诚实执行
（P013 收缩到契约层，同 imagedecoder 先例口径）。

## 验证结果

见 `test_package/MANIFEST.yml` 与 run 报告（权威 CI
`ci/conan/build_and_test.sh`，profile `ci/conan/profiles/ohos-aarch64`）。
