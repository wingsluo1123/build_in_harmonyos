# rofi 2.0.0 适配笔记

## 软件概况
- rofi：快速可定制的窗口切换器/应用启动器（C；Cairo/Pango 自绘渲染，不依赖 GTK）
- 构建系统：Meson（2.0.0）
- 上游：https://github.com/DaviDar/rofi
- 捆绑子工程：libnkutils（含 format-string/enum/colour 等模块）、libgwater-wayland、libgwater-xcb
- 产物形态：纯 CLI 应用（bin/rofi + share/ 数据 themes/desktop/icons），无对外可链接库

## 依赖拓扑（R36：16/16 配方已发布 ohpcd，conan download 实测）
```
rofi/2.0.0
├─ glib/2.84.0.1            (glib-2.0/gmodule-2.0/gio-unix-2.0)
├─ cairo/1.18.4
├─ pango/1.56.4             (pango/pangocairo)
├─ gdk-pixbuf/2.44.6.1.1
├─ libxkbcommon/1.13.1
├─ wayland/1.22.0           (wayland-client/wayland-cursor/wayland-scanner)
├─ wayland-protocols/1.36
├─ libffi/3.4.4             ┐
├─ zlib/1.3.1.1             ├ 传递 .pc 提升为直接依赖（hyprpicker/0.4.7 先例）
├─ pcre2/10.45              │
├─ graphite2/1.3.14         ┘
├─ expat/2.8.2 (override)   ┐ 版本冲突（hyprpicker 先例，API 兼容）
└─ fontconfig/2.18.1 (override) ┘
构建工具: flex/2.6.4.2, bison/3.8.2 (tool_requires)
测试框架: check/0.15.2 (test_requires)
```
阻塞路线：X11 路线需 xcb/xcb-aux/xcb-xkb/xcb-ewmh/xcb-icccm 等 5+ 依赖，未发布 → 走 Wayland。

## 构建配置
```
meson: -Ddefault_library=shared -Dxcb=disabled -Dwayland=enabled -Dimdkit=false -Dcheck=enabled
```
- `default_library=shared`：子工程 libnkutils `library()` 随动（探索构建 143/143 目标）
- `imdkit=false`：xcb-imdkit 未发布
- `check=enabled`（feature 型）：启用 3 个 check 门控测试（mode/helper_tokenize/theme_parser）

## OHOS 适配点
1. **宿主工具 .codesign 修复**（appstream/1.2.0 先例 R06）：
   wayland-scanner（wayland 包）、glib-compile-resources（glib 包）在 .conan2 包内直接执行
   报 EPERM/code=126（.codesign 失效）→ 复制到构建私有目录 +
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` +
   wrapper（export LD_LIBRARY_PATH）exec 签名副本 + 机器文件 `[binaries]` 注册
   （meson find_program 优先读机器文件）。
2. **.pc 补全**（PkgConfigDeps 只为依赖 package_info 声明的组件生成 .pc）：
   - gio-2.0：保留生成版，追加 `glib_compile_resources` 变量（meson gnome 模块需要，
     指向已签名 wrapper，无论 .pc 变量还是 find_program 解析都落到可执行副本）
   - gio-unix-2.0、gmodule-no-export-2.0（glib 包 prefix）
   - pangocairo、pangoft2（pango 包 prefix）
   - wayland-cursor（wayland 包 prefix）
   - wayland-protocols（pkgdatadir 变量，协议文件路径；该包无自带 .pc）
3. **check 0.15.2 临时文件**：P_tmpdir 编译期固定 "/tmp"（OHOS 只读）且优先级高于
   TMPDIR → 测试临时文件创建失败 `exit(2)` → build() 注入 `TEMP=<构建私有目录>`
   （check 临时目录第一优先级）；测试二进制的宿主库路径经 `LD_LIBRARY_PATH` 注入
   （aravis/0.8.36 先例；meson build rpath 只覆盖树内库如 libnkutils）。
4. **AR/AS/STRIP/NM/RANLIB 裸名环境**：OHOS worker 导出裸名但 posix_spawn 不搜索
   PATH → generate() 剔除坏值后按绝对路径固定（appstream 先例）。

## 上游缺陷修复（patches/0001-subprojects-libnkutils-core-src-format-string.c.patch）
libnkutils（捆绑子工程；上游 sardemff7/libnkutils **master 与捆绑版逐字节一致，缺陷未修复**）
`core/src/format-string.c` `_nk_format_string_parse` '/' 分支：
- count 循环经 `_nk_format_string_strchr_escape` 原位删除转义序列（反斜杠+目标字符 →
  保留目标字符），字符串尾部整体左移 1 字节，但外层 `e`（`}` 位置）未随之更新；
- 其后配对扫描 `do{…}while(w < e)` 多走一轮 → `token.replace[c].regex = NULL`
  写到 `g_new(NkFormatStringRegex, c)` 数组末尾之后 8 字节（**堆越界写**）；
- Linux 分配器 size-class 舍入（48→64）使越界落 slack 内无害（上游 CI 绿）；
  OHOS 分配器无此舍入 → 堆元数据损坏 → replace 阶段 GString 几何增长撞
  G_MAXSIZE/2（2^63）分配上限 → `GLib-FATAL-ERROR: gmem.c:177`（exit 133）/
  SIGSEGV（exit 139，随内存布局非确定）；
- 复现用例：`format-string/replace/escaping/forwardslash/3`
  （rawcount=4 + 转义 → 越界写 index 3；/1 rawcount=1 无越界；/2 越界未显现）；
- **最小修复（2 行）**：`gsize alloc = c;` + 扫描条件 `while (w < e && c < alloc - 1)`
  （配对数由 rawcount 决定，恒 ≤ alloc-1，越界轮次本就非法；正常路径行为不变）；
- 建议向上游报告（真实安全相关缺陷：小堆越界 + 平台分配器敏感）。

## 上游测试（R51 三步法）
- 测试入口：`meson test`（18 个测试程序 = libnkutils 6 套 TAP + rofi 12 个 check 套件；
  3 个 check 门控需 -Dcheck=enabled）
- 实测：**18/18 通过（100%）**，exit 0（OHOS 真机 aarch64，clang 15.0.4 原生）
- 断言统计：640 条（rofi check 12 套件 489 + libnkutils TAP 6 套 151），0 失败
- 修复前：14/18（format-string 崩溃 + 3 个 check 测试因 /tmp 只读失败）
- 测试在配方 build() 中集成（conan create 即复跑，CI 可复现）

## 消费者用例
- test_package/test.c：模拟上层桌面组件经 popen 调用 rofi 公开 CLI（`rofi -v` 版本探针），
  断言退出码 0 且输出含 "Version"；验证编译/链接/运行三段
- 实测 `rofi -v`：exit 0，输出 `Version: 2.0.0`（无需显示环境）
## CI 第 1 轮失败分析（2026-10-16，build #95940）
- **现象**：CI conan-build-test step 失败——18 个上游测试中 11 个 `exit 127`
  （全部为链接 librofi→pango→fontconfig 的 rofi check 套件；libnkutils 6 套 TAP
  + rofi:history 共 7 个通过）
- **错误**（11 处同一模式）：
  `Error loading shared library /storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so`
  `(needed by /storage/Users/currentUser/.cache/conan2/p/fontc9e10589207d96/p/lib/libfontconfig.so.1)`
- **根因**：ohpcd 预编译 fontconfig/2.18.1 包（recipe #4b3b884f，pkg #eb8a1377）的
  `DT_NEEDED` 烘焙了 expat 的**绝对路径**（构建 worker 的 CONAN_HOME 根为
  `~/.conan2`）；CI worker 的 CONAN_HOME 为 `~/.cache/conan2` → 烘焙路径不存在
  → 动态 loader 失败 → 测试二进制 exit 127（**非 .codesign 问题**：日志 0 处
  EPERM/EACCES）
- **本地 W3 18/18 的原因**（双重巧合）：① 本地 cache 有本地构建的
  fontconfig/2.18.1（pkg fontc2d246a66754ea，DT_NEEDED 为干净 soname
  `libexpat.so.1`）；② 本机 CONAN_HOME 恰为 `~/.conan2`（与烘焙根同名）
- **修复（本次提交）**：conanfile.py `_fix_absolute_needed()` 通用兼容 shim——
  扫描全部 host 依赖 .so 的 DT_NEEDED，对缺失的绝对路径在当前 cache 建指向同
  basename 真实库的符号链接（加性/幂等/非致命；本机路径已存在 → no-op；CI
  worker 构建后环境还原）。正解为 ohpcd 重发 fontconfig 改按 soname 链接
  （建议立【依赖项】任务重发 fontconfig；重发后本 shim 自动 no-op）
- **证据**：`.ohc/ci-monitor-16299/ci-95940.log`（buildbot logid 575197，19149
  行）；ohpcd fontconfig/expat 包已下载本地 cache 交叉核验（readelf 实测
  fontconfig.so.1 的 NEEDED 确为绝对路径）
---

**编译结束**: 2026-10-17 00:54
**最终状态**: built
