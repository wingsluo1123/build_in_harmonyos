# gnome-desktop 44.1 适配笔记（HarmonyOS PC / OHOS aarch64）

- 编译日期：2026-10-17
- 构建系统：Meson（上游 `meson.build`，`meson_version >= 0.56.2`）
- 源码：`https://download.gnome.org/sources/gnome-desktop/44/gnome-desktop-44.1.tar.xz`
  - sha256 `ae7ca55dc9e08914999741523a17d29ce223915626bd2462a120bf96f47a79ab`
- 构建 profile：`ci/conan/profiles/ohos-aarch64`
  （`os=OHOS os.version=6.0 arch=armv8 clang 15 libc++ cppstd=17 Release`）
- 状态: built
  （W3 本地 CI 模拟 `conan create` + `conan test` 通过；上游测试 6/12 通过，
  失败项均为平台数据缺失，详见 `reports/test-report.md`）

## 1. W0 依赖可消费性验证（先于适配）

### 1.1 直接依赖 `conan download`（R35：不用 `conan list` 判定）

```
conan download glib/2.84.0.1            -r=ohpcd  → exit 0
conan download gdk-pixbuf/2.44.6.1      -r=ohpcd  → exit 0
conan download gtk/3.24.43              -r=ohpcd  → exit 0
conan download gsettings-desktop-schemas/49.1 -r=ohpcd → exit 0
conan download xkeyboard-config/2.48    -r=ohpcd  → exit 0
conan download iso-codes/4.20.1         -r=ohpcd  → exit 0
conan download fontconfig/2.18.1.1      -r=ohpcd  → exit 0
```

日志：`$TMPDIR/gnome-desktop-44.1/logs/08-w0-dep-download.log`

### 1.2 全图可消费性（`conan install --build=never`，不含 `--build=missing`）

legacy(gtk3) 路径 27 个节点全部命中 Cache/Download，`exit 0`：

```
glib/2.84.0.1  gdk-pixbuf/2.44.6.1  gtk/3.24.43  pango/1.50.14.1.1
cairo/1.18.4   cairo-gobject/1.18.4.2  atk/2.38.0.1.1  harfbuzz/14.2.0.1.1.1
fontconfig/2.18.1.1  freetype/2.14.3  fribidi/1.0.16  libepoxy/1.5.10
libpng/1.6.58  libjpeg-turbo/3.2.0  libtiff/4.7.2  libwebp/1.6.0
expat/2.8.2.1  pixman/0.46.4  graphite2/1.3.14  libffi/3.4.4
pcre2/10.45    zlib/1.3.1.1  xz/5.6.2  zstd/1.5.7
gsettings-desktop-schemas/49.1  xkeyboard-config/2.48  iso-codes/4.20.1
```

日志：`logs/11-w0-graph-consumability-legacy.log`

### 1.3 gtk4 路径（`build_gtk4=True`）**暂不可消费** → 默认关闭

- `gtk/3.24.43` pin `pango/1.50.14.1.1`，`gtk4/4.22.4` pin `pango/1.56.4`，
  两库同一依赖图并存 → `ERROR: Version conflict: Conflict between pango/1.56.4
  and pango/1.50.14.1.1`（`logs/10-w0-graph-consumability.log` 前的
  probe 日志 `graph2.err` 已复现）。
- 在顶层用 `override=True` 统一到 `pango/1.56.4` 后，`gtk/3.24.43` 的
  package_id 变化，ohpcd **无对应 binary**：
  `ERROR: Missing binary: gtk/3.24.43:ab16f74...`。
- 仅 gtk4 路径亦缺 binary：`ERROR: Missing binary: harfbuzz/14.2.0.1:1b5bfb0...`
  （日志 `logs/12b-w0-graph-gtk4-only.log`）。

按 R36（依赖必须先发布、禁止 `--build=missing` 绕过），本版本
`build_gtk4=False, legacy_library=True`，并在 `validate()` 里对
"gtk3+gtk4 同时开启" 显式拒绝并给出原因；待依赖侧发布统一 pin 的
gtk3/gtk4 组合后，`-o build_gtk4=True -o legacy_library=False` 可直接启用。

## 2. 构建要点（配方已固化）

| # | 问题（首个错误） | 根因 | 修复 |
|---|---|---|---|
| 1 | `Missing binary: meson/1.11.0.1` | 该版本在 ohpcd 无法解析 | `tool_requires("meson/1.11.0")`（已发布且有 OHOS binary） |
| 2 | `get() got an unexpected keyword argument '44.1'` | `conan_data["sources"]` 未按版本取 | `self.conan_data["sources"][self.version]` |
| 3 | `Dependency "gio-unix-2.0" not found` | glib 配方无 `gio-unix-2.0` 组件，PkgConfigDeps 不生成该 `.pc`；MesonToolchain 的 `pkg_config_path` 只指向 conan 生成目录（不读 `PKG_CONFIG_PATH` env） | generate() 内由 `gio-2.0.pc` 派生 `gio-unix-2.0.pc` 别名 |
| 4 | `Dependency "xkeyboard-config" not found` | 依赖只发布 `xkeyboard-config-2.pc`；且包内 `share/X11/xkb` 是指向 `/share/xkeyboard-config-2` 的**绝对软链**（脱包前缀不可用） | generate() 自建 `xkeyboard-config.pc`，`xkb_base` 指向真实数据目录 `share/xkeyboard-config-2` |
| 5 | `undefined symbol: g_libintl_dgettext` | glib 2.84.0.1 的 OHOS 制品把 libintl 打进包并做符号改名（`g_libintl_*`），PkgConfigDeps 生成的 `.pc` 丢了 `-lintl` | 检测包内 `libintl.so` 存在时给 `glib-2.0.pc`/`gio-2.0.pc` 的 `Libs:` 补 `-lintl`（与 gtk 配方同法） |
| 6 | `package_info(): The direct dependency 'X' is not used by any cpp_info.requires` | conan 2 要求每个 direct require 出现在 `cpp_info.requires` | 补 `fontconfig::fontconfig`、`iso-codes::iso-codes`、`xkeyboard-config::xkeyboard-config`；`gdk-pixbuf` 用 `gdk-pixbuf::gdk-pixbuf`（非 `::gdk-pixbuf-2.0`） |
| 7 | CMakeDeps `Component 'gdk-pixbuf::gdk-pixbuf-2.0' not found` | requires 组件名用 cmake 文件名而非包名 | 改为 `gdk-pixbuf::gdk-pixbuf` |
| 8 | 测试编译 `This is unstable API. You must define GNOME_DESKTOP_USE_UNSTABLE_API` | 上游不稳定 API 宏 | 测试源首行定义该宏（与上游 `test_args` 一致） |
| 9 | `glib-compile-schemas: Operation not permitted` / `symbol not found` | HarmonyOS 执行 ELF 需 codesign；且需 `LD_LIBRARY_PATH` 指向包内 lib | test_package 内复制 + 自签名 + 注入依赖 `LD_LIBRARY_PATH` |
| 10 | `TypeError: ... not NoneType`（xkeyboard-config package_folder） | conan 把数据包列为 "Skipped binaries"，`package_folder=None` | test_package 显式 `self.requires("xkeyboard-config/2.48")` |
| 11 | XKB 布局数 0 | test_package 把 `XKB_CONFIG_ROOT` 指向了坏软链 `share/X11/xkb` | 指向 `share/xkeyboard-config-2`（实测 `layouts=598`） |

## 3. OHOS 平台行为差异（非配方缺陷，已确认）

1. **seccomp/bwrap 沙箱关闭**：上游仅当 `host_machine.system() == 'linux'`
   时探测 `libseccomp`；OHOS 的 meson host system 为 `harmonyos` →
   `ENABLE_SECCOMP=0 / HAVE_BWRAP=0`。`gnome-desktop-thumbnail` 的
   thumbnailer 沙箱脚本执行保留，但不再套 seccomp 过滤器（与上游在
   非 Linux 平台的行为一致）。
2. **`HAVE_SYSTEMD=0`**：无 systemd 依赖（`gnome-systemd.c` 的 D-Bus
   逻辑保留，运行期无 systemd 时优雅失败）。
3. **`HAVE_XKBREGISTRY=0`**：未引入 libxkbcommon（其 xkbregistry 模块在
   ohpcd 里默认关闭），`gnome-xkb-info` 走上游的 GMarkup 解析 XKB 规则
   分支（实测 `layouts=598`、`us → English (US)` 正常）。
4. **GLib 无时区数据库**：`g_time_zone_new_local()` 在 OHOS 回退 UTC
   （无 TZif 数据），与 libc `mktime()`（遵循 `TZ`）不一致 →
   上游 `bg-slide-show` 的 `starttime-no-dst` 用例失败。
5. **无 libc locale 数据库**：`gnome_get_all_locales()` 退化为
   "从翻译推断"，触发上游测试的致命 warning（`languages` 用例失败）。
6. **无显示后端**：`wallclock-reftest` 需要 `gtk_init()` 显示；broadway
   后端本机尝试未成功（`cannot open display:`），4 个用例未执行。

## 4. 配方设计要点

- `package_type = "library"`，默认 `shared=True`（依赖全为 shared 制品）。
- 选项：`shared / fPIC / build_gtk4 / legacy_library / with_introspection /
  debug_tools / with_tests`，与上游 meson 选项一一映射。
- `debug_tools=False`（默认不安装 `libexec/gnome-desktop-debug` 下的交互式
  调试程序；库包不需要，且这些是手工工具而非 API）。
- `with_introspection=False`（不产 `.gir`，避免引入 gobject-introspection
  工具链依赖；需要时打开）。
- `with_tests=True` 时在 `build()` 内签名构建产物并实际运行上游 4 个
  `g_test` 程序（含现场编译 GSettings schema）；默认关闭，因为上游测试
  依赖 locale/tzdata/显示等桌面环境数据（见 §3），CI 绿线不宜受其影响。
- 安装产物：`lib/libgnome-desktop-3.so.20.0.0`（含 `.so.20`/`.so` 软链）、
  13 个头文件（`include/gnome-desktop-3.0/libgnome-desktop/`）、
  `lib/pkgconfig/gnome-desktop-3.0.pc`（prefix 重写为包路径，剥除不存在的
  `-I`）、121 个 `.mo`（`share/locale/*/LC_MESSAGES/`）。
- OHOS 上安装的 `.so` 用 `/data/service/hnp/bin/binary-sign-tool` 自签名。
- 未使用 `patches/`：全部适配通过配方层解决（无平台宏、无源码改动）。

## 5. 复现命令

```bash
export CONAN_HOME=<repo>/_conan_home        # 或任意空目录
export PATH=<repo>/_venv_conan/bin:$PATH    # conan 2.29.1(OHOS 适配版)

# 1) 构建 + 打包 + 消费者测试（W3 等价）
conan create archives/g/gnome-desktop/44.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 2) 仅跑消费者测试
conan test archives/g/gnome-desktop/44.1/test_package gnome-desktop/44.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 3) 连上游测试一起跑（需 locale/tzdata/显示数据，见 reports/test-report.md）
conan create archives/g/gnome-desktop/44.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -o "&:with_tests=True"
```
## 6. finish 门禁状态（提交前审计记录，2026-10-17）

| 门禁 | 结果 | 证据 |
|---|---|---|
| conan-verify（G0-G4） | ✅ PASS | `reports/conan-verify-report.md` |
| W3 本地 CI（JC1-JC6 + L0/L1/L2/L4/L5） | ✅ PASS | `reports/w3-local-ci.log`：`JC_RESULT=pass`、`Junk Files: 0`（prdiff 9 文件）、`Pass rate 100.0%` |
| `.ci-result.json` | ✅ 由 finish 写入 | `integrity_hash=6fb2d49b0ed2fd09` 按 `finish.py:252` 公式可复算一致；`log_sha256` 与 `reports/w3-local-ci.log` 实测 sha256 一致 |
| `finish` 整体退出码 | ⚠️ EXIT=1（`失败步骤: step5b, step8`） | 两项均为**仓库既有状态/工具口径**问题，非本包引入，按任务要求不处理 |

`step5b`（W5 知识完整性，`scripts/ohc/workflow_checks.py:240`）：失败来自 `E###.kv`
**既有条目**的 `error_signature` / `root_cause` 字段为空（日志中 E748、E749、E788… 等
数十条），本包未新增任何知识条目（`git status knowledge/` 无改动、`manifest.yaml`
`knowledge_count=0`），即与 gnome-desktop 无关。

`step8`（submit 就绪预检，`scripts/ohc/finish.py:365`）：要求 `packaging/` 非空与
`.staging-verified` 存在，但两者在仓库规范 `knowledge/ARCHIVE-SPEC.md`（v3.0）中
已被明确废弃（第 7 行、第 242-247 行：`packaging/` 废弃、`packaging/*.tar.gz` 删除、
`.staging-verified` 废弃），且被 `.gitignore` 第 2/64/263 行忽略；为满足预检而手工
造 `packaging/` 会同时违反 R19（禁止手动打包，改用 conan create + conan upload）
与上述规范，故不创建。
---

**编译结束**: 2026-10-17 20:07
**最终状态**: built
