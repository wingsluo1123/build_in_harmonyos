# nip4 9.1.5：glib+glib2 双包共存图（gtk4 链 shared / vips 链 static）
# + meson gnome 工具变量注入 + snip 无头测试 VIPSHOME staging

## 场景

nip4 9.1.5（meson）依赖 gtk4（requires glib/2.84.0.1.1 shared）+ vips
（requires glib2/2.88.0 static）——glib 与 glib2 是两个**不同名** conan
包，同图共存，pkg_config_name 都叫 glib-2.0。

## 三查

1. **共存先例**：gtk4/4.22.4 的图已含双 glib（graphene → glib2/2.88.0
   static + pango/harfbuzz 链 → glib/2.84.0.1.1 shared，CI 通过）。
   conan override 只按同名生效，跨名（glib vs glib2）不冲突、不合并。
2. **PkgConfigDeps 同名覆盖**：glib-2.0.pc 两包都生成，后写覆盖先写，
   不报错（conan 2.31 源码确认无 duplicate 检查）——必须以
   generate() 末尾的注入步骤兜底修正内容（工具变量/包含路径），
   不能假设哪份幸存。
3. **glib bin 工具可执行性**：OHOS ELF 工具 .codesign 过期 → XPM exec
   code=126；须 llvm-objcopy --remove-section .codesign +
   binary-sign-tool -selfSign 1 原地重签（gtk4 模式），脚本类
   （gdbus-codegen shebang）跳过。

## shared glib 下依赖包自身 meson.test 的运行时库定位（2026-09-11 实证）

gtk4 的 `override=True` 把 glib/2.84.0.1.1(shared) 压到全图 → harfbuzz 在
nip4 图内源码重建（package_id 与已发布 static-glib 二进制不同）→ 其
build() 内 meson.test 165/239 全灭（PR #9517 CI #44160）：测试二进制靠
meson 注入的 RUNPATH 找到 libglib-2.0.so.0，但 musl 解析 libglib 的
NEEDED libintl.so.8 不继承该 RUNPATH → 命中系统目录、缺 g_libintl_*
符号 → `Error relocating .../libglib-2.0.so.0: g_libintl_*: symbol not
found`。根治在 glib 配方侧：shared 构建时 proxy-libintl:default_library
=static，把 intl 静态链入 libglib，从根上消除 NEEDED libintl.so.8
（下游 harfbuzz/pango/cairo/gtk4 全部受益，免逐包补丁）。该根修已由
**glib/2.84.0.2**（R37，2026-09-07 发布并进 main）持有——制品实测
`lib/` 只含 libintl.a、无 libintl.so.8，glib-2.0.pc 带
`-DG_INTL_STATIC_COMPILATION`。本配方因此在 requirements() 里
`self.requires("glib/2.84.0.2", override=True)`，把 gtk4 传递的
glib/2.84.0.1.1 顶到该根修版本。兜底备选：下游包 build() 内 glib
shared 时把 glib lib 目录前置 LD_LIBRARY_PATH 再 meson.test()。
教训：凡 build() 内
跑测试且依赖含 shared 库的包，都要把依赖 libdir 喂给测试进程；
test_package 有 conanrun 无此问题，build() 只有 conanbuild。

## override glib→2.84.0.2 的连带代价：预编译 gtk4/gdk-pixbuf 的 NEEDED libintl.so.8 悬空（2026-09-11 实证）

把图切到 glib/2.84.0.2 后，CI #44304 从 harfbuzz/gtk4 的构建期失败**前移**到
nip4 自己的 build() 测试期（说明根修起效、gtk4 二进制被复用未重建），但露出
新问题——**已发布的 gtk4/4.22.4 与 gdk-pixbuf 二进制**（构建期由 glib 制品内
proxy-libintl 满足其 `-lintl`）仍带：

```
Error loading shared library libintl.so.8: (needed by .../gtk4.../lib/libgtk-4.so.1)
Error loading shared library libintl.so.8: (needed by .../gdk-pd.../lib/libgdk_pixbuf-2.0.so.0)
```

glib/2.84.0.2 的 `lib/` 无 libintl.so.8 → NEEDED 无处可解析 → snip 启动
即 exit 127。**修法：加 host 依赖 `libintl/0.26.1`**（`archives/l/libintl`，
`package_type=library`）——该包是**合并 shim**，同一个 libintl.so.8 同时导出
`libintl_*` 与 `g_libintl_*`，故图中 glib 无论 shared（需 g_libintl_*）还是
static-intl（只需 libintl_*）都满足，正为此场景而造。**教训：去掉某制品里的
`libintl.so.8`（静态化 intl）会连带打断**已编译**下游的 NEEDED；根修需配套
补 shim，不能只改上游包。**

## GSL 的 CBLAS 独立库：libgsl.so 不 NEEDED libgslcblas（2026-09-11 实证）

同一轮 CI 还报：

```
Error relocating .../libgsl.so.28: cblas_sdsdot: symbol not found   (×~50)
```

GSL 的既定设计（`archives/g/gsl/manifest.yaml` 已记）：CBLAS 在独立
`libgslcblas.so.0`，`libgsl.so.28` **不** NEEDED 它，把 `cblas_*` 留给消费方
解析，须同时链 `-lgsl -lgslcblas`。vips/gsl 制品的 .so 未 NEEDED gslcblas
→ 测试进程里无人提供这些符号。**修法：`LD_PRELOAD=<gsl>/lib/libgslcblas.so.0`**
——测试期无法重链 snip，用预载把 cblas 符号放进全局符号域，与
`-lgslcblas` 等价。**教训：`LD_LIBRARY_PATH` 只保证「能被 NEEDED 找到」，
不保证「被加载」；库把符号留给消费方时（GSL/部分 BLAS），要么重链，要么
`LD_PRELOAD` 强制载入。**

## snip 无头测试

snip（main-snip.c）不初始化 gtk display（gtk_disable_setlocale 可在
init 前调），管道/批处理可用。运行时数据定位：get_prefix() →
vips_guess_prefix(argv0, "VIPSHOME") → 须存在 $VIPSHOME/share/nip4
（path.c:623/629 start+data）。meson test 依赖安装态布局；build()
层1 用 VIPSHOME=<staging>（copytree share/nip4）+ HOME=<可写 tmp>
（main_mkdir 建 .nip4-9.1.5/{tmp,start,data}）等价驱动 31 项。

## .ws 工作区内嵌开发机绝对路径 $HOME/GIT/nip4/...（2026-09-11 实证，CI #44328）

### 现象

`snip --test --workspace test/workspaces/test_colour.ws` 首个即失败，**0/31**：

```text
error in "xoffset" (O4.super.xoffset — .../test_colour.ws): bad arguments to get_header
error in "O4" (O4 — .../test_colour.ws): error in row O4.super.value: Not found in O4.super.value
file "$HOME/GIT/nip4/test/workspaces/images/ultra-hdr.jpg" not found on path
nip4/9.1.5: Error in build() method, line 126 self._run_upstream_tests()
```

后面的 `bad arguments to get_header` / `Not found in ...value` 都是**图像载入失败
的下游**（图 header 为空），不是独立问题。

### 根因：工作区把图像存成 `$HOME/GIT/nip4/...`，载入时按**运行期 $HOME** 展开

`.ws`（XML）里图像文件名是开发者机器的绝对路径，且以 `$HOME` 占位存储：

```xml
<Image_file>"$HOME/GIT/nip4/test/workspaces/images/ultra-hdr.jpg"</Image_file>
```

载入链：`path_find_file(of->fname)`（path.c:555）先 `existsf("%s", filename)`
精确命中；而 `existsf` → `calli_string_filename`（util.c:1566）会
`expand_variables(filename, buf)`（util.c:1294：`$VAR` → `g_getenv(vname)`；
`~` → `$HOME`）再 `nativeize/absoluteize`。故存储串被展开成
`<运行期 HOME>/GIT/nip4/test/workspaces/...`。**与 cwd 无关**
（path.c:610 注释明说不让 workspace 依赖 cwd）。

因此上游 meson test 只在「开发者 `~/GIT/nip4` 有检出」时能过；CI 里
`HOME=<可写 tmp>`（见上节）下并无 `GIT/nip4` → 每个 `.ws` 全部 miss。

### 修法：把 `$HOME/GIT/nip4` 前缀接回源码树

```python
gitdir = os.path.join(home, "GIT")          # home = 测试用 $HOME
os.makedirs(gitdir, exist_ok=True)
link = os.path.join(gitdir, "nip4")
if not os.path.lexists(link):
    try:
        os.symlink(src, link)               # src = source_folder（检出根）
    except OSError:                         # HMDFS 无符号链接权限时复制
        os.makedirs(os.path.join(link, "test"), exist_ok=True)
        shutil.copytree(os.path.join(src, "test", "workspaces"),
                        os.path.join(link, "test", "workspaces"))
```

工作区引用的全部路径都在 `$HOME/GIT/nip4/test/workspaces/` 下（22 个图像 +
`test_matrix.ws`/`test_tasks.ws` 两个嵌套工作区），故只需该前缀可达即可；
`test/snip/*.def` 与 `test_cli.sh` 用的是显式 `$SRC` 绝对路径，不受影响。

**通用教训**：vendored 上游测试套件里若工作区/工程文件内嵌了**创造者的绝对
路径**（`$HOME/...`、`$VIPSHOME/...` 占位或纯绝对路径），在 CI 的不同 `$HOME`
/ 不同检出位置下必然 miss。定位顺序：先看 `.ws`/工程文件里存的是什么串 →
再 grep 源码确认**何时展开**（此处是 file-exists 路径展开，不是加载 .ws 时）
→ 用 symlink/copy 把该前缀 stage 到展开后的目标。诊断指纹：
`file "<$VAR 占位串>" not found on path` 且错误串里的 `$VAR` **未被展开**。
