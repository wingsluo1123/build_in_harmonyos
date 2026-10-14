# at-spi2-core 2.60.5.1 适配笔记（glib 2.84 谱系变体）

## 变体说明（相对 2.60.5）

- 上游源码与版本号不变（at-spi2-core 2.60.5 tarball，sha256 见 conandata.yml），
  仅依赖谱系与适配层变更，按 R37 递增适配后缀为 2.60.5.1。
- glib 依赖：glib2/2.88.0 → **glib/2.84.0.2**（glib 谱系）。glib 与 glib2 为
  两个并列包，各生成一份 glib-2.0.pc 且钉不同 zlib（1.3.1 vs 1.3.1.1），
  不可同图混用；gtk 3.24.43 栈（pango/atk/cairo/gdk-pixbuf）构建在 glib
  谱系上，而 gtk X11 后端硬性需要本包的 atk-bridge-2.0（meson.build:568）
  → 本变体供桥。
- 2.84.0.1 → 2.84.0.2：前者 proxy-libintl 装成独立 libintl.so.8（仅导出
  g_libintl_*，缺 bindtextdomain/dgettext 等真实符号）→ 消费者链接期
  undefined；后者改 static 链接，代理实现并入 libglib-2.0.so（实测 9 个
  g_libintl_* 定义、无 libintl.so NEEDED）。曾试"gettext 真实 libintl +
  Cflags 头顺序"方案，因与 glib 自身引用冲突而回退，残留已清除。
- 本地验证：`conan create . --build=missing -pr:h ohos-aarch64 -pr:b default`
  全绿（主包 + test_package 全过，日志 ~/tmp/atspi-2.60.5.1-create.log）。

## 编译环境
- 构建系统: meson
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15（/data/service/hnp/bin，aarch64-linux-ohos）
- 状态: built（conan-verify G0-G4 全 PASS；未 upload）

## 编译步骤

```bash
# conan 配方构建（探索编译 + conan create）
python3 scripts/ohc-run.py conan-verify at-spi2-core 2.60.5.1
# 依赖：glib/2.84.0.2（pcre2/10.45、zlib/1.3.1.1、libffi/3.4.4）、
#       dbus/1.14.10（钉 expat/2.8.2）、libxml2/2.15.3.1（私有，仅 meson configure）
```

探索编译已单独通过：meson 交叉编译 281 个 target 全过，install 到
TEST_PREFIX 成功；meson test 5/9 通过，4 个失败为 OHOS 无 dbus-daemon
会话总线所致（dbind/droute/memory/atk-test 依赖可用总线），属平台限制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI worker 导出 llvm-ar/as/strip/nm/ranlib 裸名，PATH 找不到 | env 污染 | generate() 弹出 AR/AS/STRIP/NM/RANLIB，用绝对路径 ar/as/strip/nm/ranlib 锁进 MesonToolchain |
| 2 | dgettext/libintl undeclared（编译报错） | OHOS sysroot 无 gettext，libintl.h stub 无声明 | glib 谱系的 proxy-libintl 提供代理头（最终 glib/2.84.0.2 已把它静态并入 libglib-2.0.so），补写 glib-2.0.pc 增加 `-I"${prefix}/include"`（Cflags）与 glib_genmarshal/glib_mkenums 等变量 |
| 3 | dbus 包不提供 dbus-1.pc；glib2 缺 gobject/gio/gmodule 单模块 .pc | 已发布包只带聚合 .pc | generate() 补写 dbus-1.pc（Requires: expat）与 gobject-2.0/gio-2.0/gmodule-2.0 薄包装 .pc |
| 4 | zlib/1.3.1 为非-PIC 静态库 | 链进共享库报 R_AARCH64 relocation | default_library=static（shared=False）整体静态交付（R26），atk/atspi 非系统同名库无冲突 |
| 5 | test_package 编译 'glib.h' file not found | 静态库包 Conan 2 traits 优化：transitive dep 的 require.headers=False，CMakeDeps 生成 glib/dbus 的 INCLUDE_DIRS 为空 | requirements() 对 glib2/dbus 显式 `transitive_headers=True`，让 include 目录传播到下游 |
| 6 | test_package 冒烟 `at-spi-bus-launcher --version` abort | 该二进制不支持 --version（非法参数 g_error/SIGABRT），且 OHOS 无 gsettings-desktop-schemas（get_schema 即 abort）、无 dbus-daemon，无法真实运行 | test() 改用 readelf 产物级验证（可执行 aarch64 ELF）；at-spi2-registryd --help 仍真实运行 |
| 7 | at-spi2-registryd / at-spi-bus-launcher 不在 conanrun PATH | 静态库包 require.run=False，VirtualRunEnv 不把 cpp_info.bindirs 加入 PATH | package_info 用 runenv_info.prepend_path("PATH", .../bin)（模式同 a52dec） |
| 8 | 无 X11 / systemd / gobject-introspection / gtk-doc | OHOS 桌面组件缺失 | project_options: x11=disabled, use_systemd=false, introspection=disabled, docs=false, gtk2_atk_adaptor=false, dbus_glib=disabled |
| 9 | meson 把 OHOS 检测为 harmonyos 而非 linux | E090 已知模式 | 探索编译 281 target 全过、conan create 通过，无实际编译影响，未加补丁 |

## 源码修改

无补丁（patches/ 为空）。所有适配均在 conanfile.py 的 generate()/
package_info() 内完成。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.2 | 提供 gobject/gio/gmodule（2.84 谱系；proxy-libintl 已改 static，self-contained g_libintl_*） |
| dbus | 1.14.10 | dbus-1 客户端库（钉 expat/2.8.2） |
| libxml2 | 2.15.3.1 | 仅 meson configure 用（visible=False） |
| pcre2 | 10.45 | glib 传递依赖 |
| zlib | 1.3.1.1 | glib 传递依赖（非-PIC 静态） |

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify at-spi2-core 2.60.5.1
# G0 预构建评估 PASS / G1 配方完整性 PASS / G2 conan create PASS /
# G3 系统同名库隔离 PASS / G4 产物完整性 PASS
# conan create 真实通过：
#   at-spi2-core/2.60.5.1@ohpcd/stable: Created package revision ...
#   test: 'atk role API + atspi linkage verified (role=button)'
#   test: 'at-spi2-registryd --help' 正常输出 GOption 帮助
#   test: 'at-spi-bus-launcher ELF OK'（产物级验证）
```

## 上游测试实测（2026-10-04，9/9 项逐项执行）

命令：`meson test -C <build-release> --print-errorlogs`（日志 `~/tmp/atspi-meson-test.log`）
上游清单（`meson test --list`）共 9 项，全部执行：

| # | 测试 | 结果 | 说明 |
|---|------|------|------|
| 1 | testdocument | ✅ OK | ATK document 接口 |
| 2 | testrole | ✅ OK | ATK 角色 API |
| 3 | testrelation | ✅ OK | ATK relation API |
| 4 | teststateset | ✅ OK | ATK state-set API |
| 5 | testvalue | ✅ OK | ATK value API |
| 6 | dbind-test | ❌ FAIL | SIGABRT：`dbind:ERROR:../dbind/dbtest.c:386: assertion failed: (bus != NULL)`——需 D-Bus 会话总线 |
| 7 | droute-test | ❌ FAIL | SIGABRT：libdbus `dbus_connection_get_data()` 断言 `connection != NULL` 失败（dbus-connection.c:6144）——需会话总线 |
| 8 | memory | ❌ FAIL | SIGTRAP：`dbind-ERROR **: AT-SPI: Couldn't connect to accessibility bus. Is at-spi-bus-launcher running?`——需 accessibility 总线 |
| 9 | atk-test | ❌ FAIL | SIGTRAP：`Bail out! FATAL-ERROR: Could not initialize atspi, code 2`——需 accessibility 总线 |

失败 4 项的共同平台约束（非配方缺陷）：

- 平台无 `dbus-daemon` 二进制：制品仓 `dbus/1.14.10` 配方 build() 明确
  `cmake.build(target="dbus-1")`（L87-89 注释：daemon 目标在 OHOS 交叉编译下
  链接 expat 失败，本配方只需客户端库）；本机 `.conan2` 缓存、`/system/bin`、
  `/usr/bin` 均无该二进制（已实测确认）。
- `atk-test` 另需 accessibility bus（at-spi-bus-launcher）与
  gsettings-desktop-schemas，OHOS 均缺（get_schema() 即 g_error/SIGABRT）。

消费者测试（test_package，R34 实质 API 调用）1/1 通过：`test_atk.c` 真实创建
AtkObject、设置/查询角色、`atk_role_get_name()`，并对 `atspi_init`/
`atspi_get_desktop`/`atk_bridge_adaptor_init` 做链接级验证；另冒烟
`at-spi2-registryd --help`（真实 daemon 运行）与 at-spi-bus-launcher 产物校验。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（meson；components: atk/atspi/bridge） |
| conandata.yml | 官方 GNOME 源 + sha256 |
| test_package/ | CMakeDeps 消费者测试（test_atk.c + MANIFEST.yml） |
| manifest.yaml | 归档元数据 |

## 注意事项

- **无 dbus-daemon**：ohpcd 未发布 dbus 守护进程包；at-spi 总线依赖
  session bus，OHOS 上 at-spi2-registryd 可 --help 启动，但完整总线服务
  需 dbus-daemon（平台限制，后续可补）。
- **无 X11/systemd/gi**：x11、systemd、gobject-introspection 均禁用。
- **at-spi-bus-launcher 不可运行**：OHOS 缺 gsettings-desktop-schemas
  （get_schema 即 abort）且无 dbus-daemon，只能做产物级验证。
- **静态交付**：zlib 非-PIC，default_library=static；atk/atspi 非系统同名
  库，静态交付无 R26 冲突。
- **静态库 headers 传播**：本配方组件 requires 需要下游拿到 glib/dbus
  头文件，必须保留 transitive_headers=True；若去掉，消费方 CMakeDeps 的
  INCLUDE_DIRS 会变空（'glib.h' not found）。
---

**编译结束**: 2026-10-04 17:41
**最终状态**: built
