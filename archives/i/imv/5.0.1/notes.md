# imv 5.0.1 适配笔记

## 1. 上游与任务信息

- 上游: https://sr.ht/~exec64/imv/ ，tag `v5.0.1`
  （`git ls-remote --tags` 实测 `refs/tags/v5.0.1` = `3ef6039b9a13ac9ba842bf6512c9f700c16571e3`，
  deref `bdec0e527be289e08c3a70c8719a85994d26bd4d`）
- tarball: `https://git.sr.ht/~exec64/imv/archive/v5.0.1.tar.gz`
- 实测读数（本机重算）: HTTP 200 / **72953 B** /
  sha256 `8949c1df4b933b1d324e02ce49f1834a4b73dd25fa8103579e0ed105149e080e`
- 许可证: MIT；形态: **C + Meson**（`meson_version >= 0.62`，`c_std=c99`，`warning_level=3`）
- 任务: 平台任务 **7452**（主积分赛），登记表 `任务登记表.csv` 行 `7452,imv,5.0.1,主理-7`
- 包类型: `application` —— 产物为 `bin/imv`（窗口客户端）、`bin/imv-msg`（IPC 电）、
  `bin/imv-dir`（contrib 脚本）、`etc/imv_config`、`share/applications/*.desktop`

## 2. 编译环境

- 构建系统: Meson（设备原生 build == host，conan 判非 cross ⇒ meson 直接跑测试）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，取自 profile
  `tools.build:compiler_executables`）
- Conan: 2.29.1（OHOS 适配版）；profile `ci/conan/profiles/ohos-aarch64`
  （os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / Release）
- 宿主: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，A 机 8 核亲和 / 装机 20 核）
- 状态: built（本地 `conan create` 与 `conan-verify` 通过，尚未平台 upload）

## 3. 窗口系统与 GL 栈的取舍（本包最关键的决策）

上游 `meson_options.txt` **只有** `windows`（combo: `all|wayland|x11`），
**没有 `x11` 布尔选项**——`-Dx11=disabled` 会直接 `Unknown option`。本配方取
`-Dwindows=wayland`，依据两条实测：

1. 本机 `/system/lib64` 只有 `libEGL.so` + `libGLESv3.so`，**没有** libX11/libxcb/
   libwayland-client；X11 与 Wayland 运行环境都不存在；
2. X11 路在本仓**结构性不可行**：`libxkbcommon/1.6.0` 配方显式禁用 x11 模块
   （不产出 `xkbcommon-x11.pc`），而 `meson.build` 的 `deps_for_x11` 硬需
   `dependency('xkbcommon-x11')`。
   wayland-only 同时使 `target_single_ws = true` ⇒ 可执行名就是 `imv`。

GL/EGL（ohpcd **无 `opengl/4.6`**，W0 实测 MISS）：

- imv 的画布是**桌面 GL 1.x 固定管线**（`src/canvas.c`：`glBegin/glVertex2i/
  glTexCoord2f/glOrtho/glPushMatrix`），GLES2 头里没有这些符号 ⇒ 必须用
  **gl4es/1.1.6**（固定管线→GLES2/EGL 翻译层），不能用 `gles2/2.0.25`；
- gl4es 只装 `lib/libGL.so`+`include/GL`，**不装 .pc** ⇒ 配方自建 `gl.pc`
  （`Libs: -lGL`）指向 gl4es 包，`dependency('gl')` 直接命中，上游 meson.build 零改动；
- 实测 gl4es 的 `libGL.so.1` **不导出 EGL API**（`llvm-nm -D --defined-only` 里
  `T egl*` 命中 0，只有数据符号 `egl`）⇒ EGL 必须由 **egl/1.0.5**（静态 `libEGL.a`，
  dlopen 转发 `/system/lib64/libEGL.so`）提供，同样自建 `egl.pc`；
- gl4es 的初始化发生在 **`libGL.so.1` 的构造函数**里：实测「空 main + `-lGL`」
  在缺 `LIBGL_GLES`/`LIBGL_EGL` 时**加载期 SIGSEGV**，设置这两个变量后完整初始化成功
  （`LIBGL: Using GLES 2.0 backend` / `Max texture size: 8192` / rc=0）。
  配方 `package_info()` 因此用 `runenv_info` 导出
  `LIBGL_GLES=/system/lib64/libGLESv3.so`、`LIBGL_EGL=/system/lib64/libEGL.so`
  （与 gl4es 自己的 test_package 同款）。

## 4. 编译步骤（已固化为 conanfile.py）

```bash
conan create archives/i/imv/5.0.1 \
  -pr:h=<root>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<root>/ci/conan/profiles/ohos-aarch64 \
  --build="imv/*" -c tools.build:jobs=$BUILD_SLOT_JOBS
```

配方内部顺序：

1. `source()`：imv v5.0.1 + wayland 1.24.0 源码（后者仅用于静态编译 wayland-scanner）
2. `generate()`：`PkgConfigDeps` + `MesonToolchain`；写 `fixed_pkgconfig/`
   （自建 `gl.pc`/`egl.pc`/`wayland-scanner.pc`/`wayland-protocols.pc` + 依赖 `.pc`
   改写 prefix/libdir/includedir 并把 `.pc` 里失效的 `-L` 指回真实 libdir）；
   写 pthread-cancel 兼容 TU 的 `.h`/`.c`；native file 注入 `llvm-ar`/`llvm-ranlib`/
   `ninja`/`xxd`；`extra_cflags += -include <compat.h>`；`extra_ldflags += <compat.o>`
   与每个依赖 libdir 的 `-Wl,-rpath`
3. `build()`：先编译 pthread-cancel 兼容 `.o`，再静态编译 wayland-scanner，
   然后 `meson.setup()/build()/test()`
4. `package()`：`meson install`，随后对 `bin/imv`、`bin/imv-msg` 重新签名（见问题 9）
5. `package_info()`：`bindirs=["bin"]` + gl4es 运行期 `LIBGL_*`

## 5. 依赖版本

直接依赖（`requirements()`）：

| 依赖 | 版本 | 用途 |
|------|------|------|
| pango | 1.50.14.1.1 | `dependency('pangocairo')`（overlay 文字渲染；与 librsvg 定点一致） |
| gl4es | 1.1.6 | `dependency('gl')`（自建 `gl.pc`）桌面 GL 固定管线→GLES2 |
| egl | 1.0.5 | `dependency('egl')`（自建 `egl.pc`）静态 libEGL.a 转发系统 EGL |
| libxkbcommon | 1.6.0 | `dependency('xkbcommon')` 键盘布局 |
| icu4c | 77 | `dependency('icu-uc')`（`-Dunicode=icu`） |
| inih | r58 | `dependency('inih')`（配置解析） |
| wayland | 1.24.0 | `wayland-client` / `-cursor` / `-egl` 与 `.pc` |
| wayland-protocols | 1.36 | `stable/xdg-shell` + `unstable/pointer-gestures` XML |
| libffi | 3.4.4 | `wayland-client.pc` 的 `Requires.private: libffi` 需实际安装 |
| pcre2 | 10.45 | `glib-2.0.pc` 的 `Requires.private: libpcre2-8`（Skipped binary，须提升） |
| graphite2 | 1.3.14 | `harfbuzz.pc` 的 `Requires.private: graphite2`（同上） |
| xz | 5.6.2 | `libtiff-4.pc` 的 `Requires.private: liblzma`（同上） |
| xorgproto | 2025.1 | `libx11/libxrender/libxext.pc` 的 `Requires: xproto/kbproto/renderproto/xextproto`（同上） |
| libpng | 1.6.58 | PNG 后端（`dependency('libpng')`） |
| libtiff | 4.7.2 | TIFF 后端（`dependency('libtiff-4')`，与 gdk-pixbuf 定点一致） |
| libjpeg-turbo | 3.2.0 | JPEG 后端（`dependency('libturbojpeg')`） |
| librsvg | 2.62.3.1.1 | SVG 后端（`dependency('librsvg-2.0')`） |
| libnsgif | 1.0.0 | GIF 后端 |
| libnsbmp | 0.1.7 | BMP/ICO 后端 |
| libheif | 1.22.2 | HEIF/AVIF 后端 |
| libwebp | 1.6.0 | WebP 后端（`dependency('libwebpdecoder')`，与 libtiff 定点一致） |
| cmocka | 2.0.2 | 上游测试套件（`-Dtest=enabled`） |

版本冲突消解（`override=True`，均为实测）：

| override | 原因 |
|---|---|
| expat/2.8.2.1 | wayland 定 2.8.2，libxml2 侧定 2.8.2.1 |
| libxml2/2.15.3.1 | wayland 定 2.15.3，librsvg 定 2.15.3.1 |
| libxrender/0.9.12.1 | cairo-gobject `override libx11→6.4.0` 后，libxrender/0.9.12 的已发布 binary 因 `package_id` 变化缺失（`--build=never` 硬失败）；**0.9.12.1 的已发布 binary 正是 libx11/6.4.0 世代** |

工具依赖：`meson/1.11.0`（设备无系统 meson）、`tinyxxd/1.3.16`（见问题 3）。

## 6. 上游测试用例统计（五维账本）

| 维度 | 读数 | 说明 |
|---|---|---|
| `N_static` | **6** | `test/*.c` 里 `cmocka_unit_test(...)` 文本声明：`list.c` 1、`backends.c` 3、`navigator.c` 2 |
| `N_registered` | **3** | `meson.build` 的 `foreach test : ['list','navigator','backends']` ⇒ 3 个 `test()` 目标 |
| `N_executed` | **5** | `meson test` 实测：`test_list` 1/1、`test_navigator` 1/1、`test_backends` 3/3 |
| 未执行分类 | **1** | `test/navigator.c` 的 `test_navigator_add_remove` **在上游源码里被注释掉**（第 118 行）⇒ live 5 条；未删改、也不从静态分母删除 |
| `N_consumer` | **2** | `test_package`：`bin/imv-msg`（行为面 3 断言）+ `bin/imv`（结构面 9 + 旁证面 2） |

`meson test` 原始读数：`Ok: 3 / Fail: 0`，三个测试二进制分别
`tests: 1 test(s) run. [ PASSED ] 1 test(s).`、
`tests: 1 test(s) run. [ PASSED ] 1 test(s).`、
`tests: 3 test(s) run. [ PASSED ] 3 test(s).` ⇒ **执行项 5/5，静态全量 5/6（1 条上游自注释）**。

## 7. 遇到的问题与解决方案

| # | 问题（首条真实错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Package 'libpcre2-8', required by 'glib-2.0', not found` | conan 2 把**纯传递**依赖标为 "Skipped binary" 不安装 ⇒ 其 `.pc` 不在 `PKG_CONFIG_PATH`，而 `pkg-config --cflags` 会解析 `Requires.private` | 把 pcre2/graphite2/xz/xorgproto 提升为直接 `requires`（libffi 同款先例），并补 `PkgConfigDeps` + generators 目录入路径 |
| 2 | `ld.lld: error: unable to find library -licuuc`（`-L//lib`） | `icu4c/77` 的 `icu-uc.pc` 写作 `prefix = /`（**`=` 两侧有空格**），按 `^prefix=` 改写的正则未命中 | 正则容忍空白（`\s*=\s*`）；并新增 `.pc` 落盘自检：`prefix/libdir/includedir` 或 `-L` 指向不存在目录即**硬失败** |
| 3 | `/usr/bin/xxd: Unknown option 'n'` | OHOS 的 `/usr/bin/xxd` 是 **toybox applet**，既无 `-n` 也无 vim 兼容的 `-i`；上游用 `xxd -n NAME -i IN OUT` 内嵌两张测试图 | `tool_requires("tinyxxd/1.3.16")`（vim-xxd 兼容），把 `xxd = '<path>'` 注入 meson machine file 的 `[binaries]`（meson 优先查该节，PATH 顺序不可靠），并把软链目录前置到 PATH 作第二道 |
| 4 | `undefined symbol: cairo_gobject_line_join_get_type` → 继而 `undefined symbol: xmlParseDocument` | **librsvg 制品是静态归档 `librsvg-2.a`**，其 `.pc` 把整条闭包放在 `Requires.private`，而 `pkg-config --libs`（非 `--static`）不展开私有依赖 | 在本配方复制出的 `librsvg-2.0.pc` 里把整条 `Requires.private` **提升为 `Requires`**（meson 随之补 `-rpath`），上游源码零改动 |
| 5 | `unable to find library -lfreetype` | `freetype/2.14.3` 的 `freetype2.pc` 里 `Libs: -L//lib -lfreetype`（打包期把 `${libdir}` 展开成了 `//lib` 字面量） | `.pc` 改写循环额外修复**失效的 `-L`**：指向不存在目录或以 `//` 开头 ⇒ 改写成 `${libdir}` |
| 6 | `meson ... Executables created by c compiler ... are not runnable`（sanity_check rc=127，`Error loading shared library libcairo-gobject.so.2`） | 曾把 `-lcairo-gobject` 放进 `tc.extra_ldflags`，它同样作用于 **configure 期 sanity check**，使该探针二进制多出一条找不到的 `DT_NEEDED` | 撤掉全局 `extra_ldflags`，改为**在 `.pc` 层**修（与问题 4 同一处改动），sanity check 保持干净 |
| 7 | 链接 `imv` 报 `undefined symbol: pthread_cancel` | OHOS 对 POSIX 线程取消 API **三层缺失**：① SDK sysroot 的 `<pthread.h>` 完全不声明（`grep -c` = 0，`c_std=c99` 下是编译错误）② sysroot 的桩 `libc.so` 不导出 ③ 运行时 `/system/lib64/libc.so` 虽导出却是**空壳**（返回 ENOSYS，随后 `pthread_join` 永不返回）。imv 的关闭路径正是 `cancel→join`（`src/imv.c:1242`） | 按**正式条目 E513**（`rec_approach=guarded-signal-thread-exit`；其 `rec_command` 即 `pthread_kill(thread, SIGUSR1)` + `pthread_join`）自建兼容 TU（**零上游补丁**）：`pthread_cancel` 首次调用时装 **SIGUSR1** handler（RT 信号在 OHOS 被静默吞掉，SIGUSR1 实测可用），handler 内 `pthread_exit(PTHREAD_CANCELED)`，从而真正恢复「取消即解除阻塞、join 能返回」；再用 `-include` 强制声明 + 把编出的 `.o` 挂到链接行。imv 自身不使用任何信号（实测 `src/` 无 `SIGUSR1/sigaction/signal()`），占用 SIGUSR1 安全 |
| 8 | `imv:test_backends FAIL exit status 127`（`Error loading shared library libfribidi.so.0`、`libpixman-1.so.0`、`libzstd.so.1`、`libexpat.so.1`） | meson 只为**直接** pkg-config 依赖生成 `-rpath`；pango/cairo/libtiff/fontconfig 的**传递**共享库不在其中；而 `conanbuild` 环境只带构建上下文 | `tc.extra_ldflags += -Wl,-rpath,<每个依赖 libdir>`（**不能**用 `LD_LIBRARY_PATH`：conan 的 `libintl` 代理会遮蔽系统同名库，实测直接把 `python3`/`meson` 打挂：`libpython3.14.so.1.0: libintl_dgettext: symbol not found`） |
| 9 | 安装后 `bin/imv`/`bin/imv-msg` 若无有效 `.codesign` 则内核拒绝执行（E077） | meson install 会就地改写 ELF（RUNPATH 绝对路径→占位符）使链接器写入的 `.codesign` 失效 | `package()` 末尾 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`（chayang/E472 先例） |

## 8. 源码修改

**无补丁**（`patches: {}`）：GL/EGL/wayland-scanner/wayland-protocols 全部通过配方自建
`.pc` 解决；librsvg 静态闭包与 icu 的 C++ 运行库在 `.pc` 层修正；pthread_cancel
用兼容 TU + `-include` 解决。`conandata.yml` 的 `patches` 为空但配方仍保留
`export_sources()` / `apply_conandata_patches()`（G1 门禁要求）。

## 9. 后端清单（显式，不静默）

- **启用（9）**：farbfeld、libtiff、libpng、libjpeg-turbo、libRSVG、libnsgif、
  libnsbmp、libheif、libwebp。配方对这些后端显式 `=enabled`（缺依赖即 configure 硬失败）。
  `imv -h` 打印的 `Name:` 列表与之逐项一致（消费者测试断言 9/9）。
- **显式 `disabled`（2）**：
  - `libjxl`：**ohpcd 未发布 libjxl/0.11.2**（W0 实测：`conan download --only-recipe
    libjxl/0.11.2` 与 `libjxl/0.11.2@ohpcd/stable` 双形态均 MISS），故显式关闭并披露；
  - `qoi`：上游用 `cc.has_header('qoi.h')` 探测**系统头**（不认 pkg-config），
    OHOS sysroot 无该头，故显式关闭。

## 10. 验证结果

```bash
# 上游测试（build() 内 meson.test()）
Ok: 3  Fail: 0     # test_list 1/1, test_navigator 1/1, test_backends 3/3 ⇒ 5/5

# 消费者测试（test_package，env=conanrun）
== consumer test summary: passed=14 failed=0 skipped=0 ==
#  行为面 3：bin/imv-msg 可执行 / 无参 ⇒ "Usage:" rc=0 / <不存在pid> quit ⇒ "Failed to connect" rc=1
#  结构面 9：bin/imv 可执行、.codesign 非空、6 条 DT_NEEDED、bin/imv-dir 可执行
#  旁证面 2：imv -h 输出 "imv 5.0.1"、后端 9/9
```

## 11. 运行时限制（如实披露）

1. **本机无 Wayland compositor**（`/system/lib64` 无 libwayland-client，也无
   compositor），GUI 面**不可测**：窗口创建、渲染、IPC 均无法在本机端到端验证。
   可测面已挖到底 = 上游 3 个 cmocka 测试目标（5/5 真跑）+ 安装态二进制的
   argv/socket 行为与产物结构。
2. **`bin/imv` 在无修复环境下不可直接运行**，首条真实错误：
   ```
   Error loading shared library libwayland-cursor.so.0: (needed by ./imv)
   Error relocating ./imv: wl_cursor_theme_destroy: symbol not found
   ```
   `dlopen()` 实测真因是 **EACCES（`.codesign` 校验失败）**，来自**出厂的
   wayland 制品包**，与本配方无关：
   - wayland **1.24.0 与 1.22.0.1 两版均复现**（全新 `CONAN_HOME` 从 ohpcd 重下；
     `libwayland-client`/`libwayland-egl` 可加载，**只有 `libwayland-cursor` 报
     `Permission denied`**）；
   - 同一文件 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign
     -selfSign 1` 后 `dlopen` 通过 ⇒ 失效的是 `.codesign` 本身（LOAD 段偏移/对齐
     前后一致，排除对齐问题）；
   - 根因应是 wayland 配方 `package()` 只 `meson.install()`：安装期 ELF 改写作废了
     链接器的 `.codesign` 占位，而配方**未重签**。
   消费者测试第 3 组因此**明确标注为「外部缺陷复现旁证」**：先复现该错误，再对本
   地副本重签后跑通 `imv -h`，以证明 imv 产物本身健全。
3. **`libheif.so` 无 SONAME**（`llvm-readelf -d` 无 `SONAME` 条目）⇒ 消费者
   `DT_NEEDED` 被写成**绝对路径** `/…/p/libheif.so`，跨 conan cache 不可移植
   （同样是制品包问题）。
4. gl4es 的 `libGL.so.1` 构造函数需要 `LIBGL_GLES`/`LIBGL_EGL` 指向系统
   GLES3/EGL，否则加载期 SIGSEGV；本包 `package_info()` 已用 `runenv_info` 导出。

## 12. 交付物

| 文件 | 说明 |
|------|------|
| `bin/imv` | Wayland 图像查看器（wayland-only；GL 走 gl4es，EGL 走 egl/1.0.5） |
| `bin/imv-msg` | 向运行中的 imv 发送 IPC 命令 |
| `bin/imv-dir` | `contrib-commands` 提供的包装脚本 |
| `etc/imv_config` | 默认配置 |
| `share/applications/imv.desktop`、`imv-dir.desktop` | 桌面项（MIME 列表由实际启用的后端生成） |

## 12b. 知识贡献与查重（B判定=create）

- 本包 pthread_cancel 的处置与正式条目 **E513**（`guarded-signal-thread-exit`：装
  narrowly-scoped thread-exit handler + `pthread_kill(thread, SIGUSR1)` + `pthread_join`）
  **同症状、同核心机制**；但按手册/03 §6.2 **注 2**（"用的是既有条目没写的另一条解法
  不算 hit —— 多一条可选路径 + 其适用面与代价本身就是可复用知识"）判 **create**：
  - E513 的 `rec_impl` 是 **source-patch**（改上游创建线程/取消点处）；
  - 本包是**零上游补丁的配方侧注入**（`patches: {}` 实测），并增补两条 E513 未载的平台事实
    （运行时 `pthread_cancel` 导出但返回 ENOSYS(38) 空壳；RT 信号被静默吞、仅 SIGUSR1 可用）。
- 同 PR 成对交付草稿：`knowledge/drafts/DRAFT-imv-5.0.1-pthread-cancel-ohos-nonRT-signal-shim.{kv,md}`
  （`draft-review` 三项预检 signature/root_cause/rec 全绿），并建 Issue #4226 双向互链。
- **本包相对 E513 的差异（增量精化，不是新机制）**：
  1. 交付形态：E513 的 `rec_impl` 是 `source-patch`（改上游创建线程/取消点处）；本包是
     **零上游补丁的配方侧注入**（配方写兼容 TU + `-include` 声明头 + 把 `.o` 挂链接行，
     `patches: {}` 实测），对"打包他人上游"的场景可直接复用；
  2. handler 退出码：E513 用 `pthread_exit(0)`，本包用 `pthread_exit(PTHREAD_CANCELED)`，
     使 `pthread_join(&retval)` 能拿到 PTHREAD_CANCELED，保留真实取消语义。
- **两条平台事实**（本包实测，E513 未载，已另立反馈档）：运行时 `/system/lib64/libc.so`
  虽导出 `T pthread_cancel` 但调用返回 **ENOSYS(38)**（空壳）；**RT 信号在 OHOS 被静默吞掉**
  （`sigaction`/`pthread_kill` 均 rc=0 而 handler got=0；SIGUSR1 got=1）——
  后者推翻经验库 12d §4 记的「SIGRTMIN + pthread_exit」路线。
- **纪律（本次踩到并已纠正）**：复用他人/池件的 `dedup_notes` 之前**必须自己跑一遍四范围查重**
  （`draft-review` + 逐字回读 TOP 命中条目）。本包最初照抄配送池
  `DRAFT-spiped-1.6.4-pthread-cancel-ohos-nonRT-signal-shim` 的 dedup 结论（它只比了
  E085 / 12d §4 / 12b，漏了 E513/E1078）得 create；跑 `draft-review` 后 TOP1 即 **E513**，
  逐字回读确认解法全覆盖 ⇒ 改判 hit。

## 13. 注意事项

- `-Dwindows=wayland` 是唯一可行档（见 §3）；不要照抄「`-Dx11=disabled`」这种
  上游不存在的选项名。
- 本包**不需要**任何上游补丁；改动全部集中在配方的 `generate()`（`.pc`/machine file/
  兼容 TU）与 `package()`（签名）。
- 若日后 wayland 制品包重签修好，消费者测试第 3 组的「重签副本」步骤可去掉，
  直接运行 `bin/imv -h`。
---

**编译结束**: 2026-10-18 07:19
**最终状态**: published
