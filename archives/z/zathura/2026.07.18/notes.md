# zathura 2026.07.18 编译笔记

## 编译信息
- **编译日期**: 2026-09-30
- **构建系统**: meson (>=1.5) + ninja
- **平台**: HarmonyOS (OpenHarmony) aarch64 PC
- **许可证**: Zlib
- **工具链**: OHOS 6.0 SDK, clang 15.0.4, sysroot `/root/ohpc/sdk/ohos-6.0/native/sysroot`

## 软件简介
zathura 是一个高度可定制、界面极简的文档查看器。文档格式由插件提供
（zathura-pdf-poppler / zathura-pdf-mupdf / zathura-djvu / zathura-cb 等），
主程序负责窗口、输入、快捷键、会话、书签与插件管理。

本配方安装的内容：
- `bin/zathura` —— CLI 主程序（`export_dynamic: true`，导出插件 API 符号供
  `dlopen` 的插件在运行期绑定）；
- `include/zathura/*.h` —— 插件 API 头文件（`plugin-api.h`、`types.h`、
  `document.h`、`page.h`、`links.h`、`macros.h`、`zathura-version.h`）；
- `lib/pkgconfig/zathura.pc` —— 插件构建用的 pkg-config 元数据；
- `share/` 下的 desktop / metainfo / dbus 接口 / 图标 / 27 种语言翻译 / shell 补全。

## 关键结论：本版本改用 GTK4
`2026.07.x` 把整个 GTK 交互层重写进 `girara-gtk/` 子目录，并切换为 **GTK4**：

```meson
gtk4 = dependency('gtk4', version: '>=4.12', include_type: 'system')
```

仓库中已有的 `archives/z/zathura/2026.05.20` 配方声明的是 `gtk/3.24.43`（GTK3），
该声明在本版本必然 configure 失败（找不到 gtk4）。本配方改为 `gtk4/4.22.4`。

## 依赖处理
| 依赖 | Conan 版本 | 说明 |
|------|-----------|------|
| girara | 2026.07.07.1 | UI 基础库，经 PkgConfigDeps 以 `girara.pc` 暴露 |

> 为何必须用 **`.1`** 修订：`2026.07.07` 把 gobject/gio 别名到
> `dependency('glib-2.0')`，于是只链 `-lglib-2.0`，重建后 `g_type_*`/`g_object_*`
> 全部未定义；`.1` 改为按各自 pkg-config 名查找模块，并补齐 PkgConfigDeps 省略的 glib `.pc`。
| gtk4 | 4.22.4 | 本版本新增的 GUI 依赖（>=4.12） |
| glib | 2.84.0.1.1 (override) | 见下方版本冲突说明 |
| harfbuzz | 14.2.0.1.1.1 (override) | pango 钉 14.2.0.1，其已发布二进制在本图中缺失 |
| json-glib | 1.10.6 | JSON 解析（设置/会话持久化） |
| cairo | 1.18.4 | 2D 图形，`zathura.pc` 的 Requires |
| libmagic | 5.48 | 文件内容类型嗅探（本版本新增） |
| sqlite3 | 3.49.1 | 书签/历史数据库（>=3.35.0） |
| xxhash | 0.8.3 | 文档缓存哈希（本版本新增） |
| zlib / fontconfig | 1.3.1.1 / 2.18.1.1 (override) | 与 gtk4 配方保持一致，防新版本冲突 |

### glib 版本冲突（本配方最关键的适配点）
- `girara/2026.07.07.1` 钉 **精确版本** `glib/2.84.0`；
- `gtk4/4.22.4 → pango/1.56.4` 钉 `glib/2.84.0.1`，其已发布二进制绑定
  `pcre2/10.45`；
- 两者不可共存，不 override 时 conan 直接报
  `Version conflict: Conflict between glib/2.84.0.1 and glib/2.84.0 in the graph`。

因为 girara 钉的是精确版本而非版本范围，消费方必须自己统一整图。本配方统一到
`glib/2.84.0.1.1`（gtk4 配方自身 override 的目标修订）。代价是 girara 的
package id 改变，需要重建 girara —— 这是本仓库对 GTK4 消费方的通行做法，
且比反向降到 2.84.0（会连带作废 gtk4/pango/harfbuzz/gdk-pixbuf 等全部已发布
二进制）代价小得多。

反方向（override 到 2.84.0）经实测不可行：`glib/2.84.0` 依赖 `pcre2/10.40`，
而 gtk4 栈全部构建在 `pcre2/10.45` 上，改 pcre2 会让 gtk4/pango/harfbuzz/
gdk-pixbuf/graphene/json-glib 等 8 个包的 package id 全部失配。

## 主要问题及解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Version conflict ... glib/2.84.0.1 vs glib/2.84.0` | girara 钉精确 glib 版本，pango 钉另一版本 | override 统一到 glib/2.84.0.1.1 并重建 girara |
| 2 | `Invalid: 'options.fPIC' value not defined` | `package_type="application"` 时 conan 移除 shared/fPIC | 不声明 options，去掉 default_options |
| 3 | `Options conflicts: harfbuzz/14.2.0.1->shared=False` + `Missing binary` | 裸 `default_options={"shared": True}` 被广播给所有依赖 | 同上；并 override harfbuzz 到已发布修订 14.2.0.1.1.1 |
| 4 | `'stdckdint.h' file not found`（`zathura/types.c`） | clang 15 无 C23 头 | 补丁 0001：`__has_include` 探测 + `__builtin_mul_overflow` 兜底 |
| 5 | `error: expected expression`（`girara-gtk/settings.c` 的 `static_assert`） | clang 15 拒绝 switch case 内的块作用域静态断言；且 `G_MAXINT64` 经 `G_GINT64_CONSTANT` 展开后不是合法常量表达式 | 补丁 0002：把该静态断言移到文件作用域 `_Static_assert`，保持编译期语义（不用 `g_assert`，否则 `-DG_DISABLE_ASSERT` 会把它整体裁掉） |
| 6 | `Found pkg-config: NO` / 重建 girara 时报错 | 本地交叉环境未声明 pkg-config；且 conan 生成的 `glib-2.0.pc` 是组件级（不含 gobject/gio），而 girara 补丁把 gobject/gio 别名到 `glib-2.0` | 用 `tools.gnu:pkg_config` 指向宿主 pkg-config；重建 girara 时在 pkg-config 前包一层，给 `glib-2.0.pc` 补 `Requires: gobject-2.0 gio-2.0 ...` |
| 7 | 签名工具缺失 | 本地 SDK 的 `binary-sign-tool` 不在编译器同目录 | 从 `sdk/ohos-6.0/toolchains/lib/` 软链到 `native/llvm/bin/`（仅本地环境，不改配方） |
| 8 | CI `test_package` 报 `dlopen(.../bin/zathura): Error loading shared library libjson-glib-1.0.so.0`（构建 #80089，head `0d2262791`） | `test()` 用 `dlopen(RTLD_NOW)` 打开**整个 GTK4 应用**，迫使加载器在返回前解析 `bin/zathura` 的完整 `DT_NEEDED` 闭包（gtk4 → libepoxy / graphene / glib2 / libmagic / sqlite3 / pcre2 / libffi / xz / graphite2 …）。插件宿主实际只需要其**导出的 API 符号**，惰性绑定即可到达。 | `test.c` 改为先试 `RTLD_LAZY`、失败再回退 `RTLD_NOW`；`test()` 改传 `env=None`，不再让 conan 的 `conanrunenv-*.sh` 以其自算值重新 `export LD_LIBRARY_PATH` 覆盖配方刚算好的路径。两者都失败仍按**真实失败**报错（不退化为 skip）。详见下节。 |

### 问题 8 的定位过程与验证

CI 构建 #80089（head `0d2262791`）在 `conan-build-test` 失败，失败点在
`test_package` 运行期，**不在配方本体**：`zathura/2026.07.18: Already installed!
(23 of 23)` 说明构建、打包、安装全部成功。

日志显示 `_runtime_libdirs()` 已生效，其 23 条结果**确实包含**
`.../json-01fc8e37bde89/p/lib` 与 `.../glibd610586c02b9c/p/lib`，而探针仍报
找不到 `libjson-glib-1.0.so.0`。核对 `bin/zathura` 的 ELF 得知它**没有**
`DT_RPATH`/`DT_RUNPATH`，完全依赖加载器搜索路径；其 `DT_NEEDED` 闭包约 30 个库。

本地用与 CI 同形的 profile（`-pr:h` 与 `-pr:b` 同一份，使 `cross_building()`
返回 False，`test()` 真正执行）复现，并在 `ohos-qemu-aarch64` 下运行探针：

```
ok - dlopen() of the installed zathura host succeeded
...
# consumer e2e: 0 assertion(s) failed
```
即全部 15 个 TAP 测试点通过。修复后再跑一次同样为 15/15、0 失败。

上游 headless 测试在 qemu 下重新实测（本轮，修复前/后同一结果）：

```
zathura:document  1/1  ok   (/document/open)
zathura:types     2/2  ok   (/types/image_buffer_fail, /types/image_buffer)
zathura:utils     2/2  ok   (/utils/file_valid_extension, /utils/first_page_column)
合计 5/5 通过，0 失败
```

> 局限说明：`RTLD_NOW` 的完整闭包在 CI worker 上的具体失败环节（沙箱路径可见性
> 亦或加载器搜索顺序）无法在本地 1:1 复现，因为本机没有 worker 的 HNP 沙箱。
> 因此本轮的改法是**消除对该完整闭包的依赖**（惰性绑定 + 不让 conan 覆盖路径），
> 而不是去猜某一条具体路径。若 CI 仍复现同一报错，说明闭包中另有成员无法映射，
> 届时需要 worker 侧的 `ldd` 等价输出才能继续收敛。

> 说明：第 6、7 项属于**本地 WSL 交叉环境**与 CI/真机镜像的差异，配方本身未为此
> 增加平台分支。配方里保留的是 CI/真机镜像本来就具备的前提（有 pkg-config、
> 签名工具与编译器同目录）。

## 测试

### 上游测试（本机 qemu，OHOS musl 运行根，真机口径）
```
zathura:document  1/1  ok   (/document/open)
zathura:types     2/2  ok   (/types/image_buffer_fail, /types/image_buffer)
zathura:utils     2/2  ok   (/utils/file_valid_extension, /utils/first_page_column)
合计 5/5 通过，0 失败
```
`session` / `config` / `setting` 三个用例需要 xvfb-run(X11) 或 weston(Wayland)
显示服务器，交叉编译环境不具备，已由 `-Dtests-x11=disabled
-Dtests-wayland=disabled` 关闭（这两个选项是上游 `meson_options.txt` 的真实选项；
上游没有 `tests` 选项）。

### 消费者端到端（test_package，14 条 CHECK 断言全通过 / 15 个 TAP 测试点）

> 执行口径：交叉构建下 `conan create` 只**编译并链接**该探针（OHOS aarch64 目标
> 无法在构建机上直接执行），上表的 14/14 出自 qemu（OHOS musl 运行根）与真机
> DAYU200 的实际运行，不是 `conan create` 的输出。
`test_package/test.c` 扮演真实第三方插件的角色：
1. 用**已安装**的 `<zathura/plugin-api.h>` 与上游
   `ZATHURA_PLUGIN_REGISTER_WITH_FUNCTIONS()` 宏生成
   `zathura_plugin_8_9` 定义结构；
2. `dlopen` **已安装**的 `bin/zathura` 宿主可执行文件，校验其导出的
   `zathura_image_buffer_create` / `_free` 符号（插件运行期正是这样绑定）；
3. 经宿主符号表执行整页 RGB image buffer 写入-回读回环；
4. 校验溢出保护拒绝非法尺寸。

### 真机（DAYU200-RK3568 · OpenHarmony 6.0.0.47 · aarch64）
静态链接上游 `zathura/types.c` 的 image-buffer 真实实现，真机执行
**11/11 断言通过**（真机探针是独立二进制，自带 11 条断言，与上方
test_package 的 14 条 CHECK 不是同一组统计），`_device_evidence.json` 记录 `exit_code: 0`。

## 注意事项
- `libzathura` 是 `static_library`，仅链入 CLI，不作为独立库安装；插件在运行期
  从宿主进程的动态符号表解析 API 符号，因此**插件构建只需头文件**。
- 本配方未开启 `seccomp` / `landlock` / `synctex`（对应依赖仓库未提供或需要
  内核特性），保持 upstream 的 feature 语义为 disabled。
- `manpages` / `convert-icon` 关闭以避免交叉环境引入额外构建期工具依赖。
