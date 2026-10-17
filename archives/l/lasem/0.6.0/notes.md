# lasem 0.6.0 适配笔记

## 基本信息

- 软件: lasem (SVG + MathML 渲染库, DOM 风格 API, 纯 C)
- 上游版本: 0.6.0
- 上游仓库: https://github.com/LasemProject/lasem
- 源码包: https://github.com/LasemProject/lasem/releases/download/0.6.0/lasem-0.6.0.tar.xz
- sha256: 991a23debf7e2c5683516d7a90eca112a9c985252e984d0e3410691d7e1159ea
  (MSYS2 MINGW-packages mingw-w64-lasem PKGBUILD 同 URL 同哈希;
   真机 preflight 在 gh-proxy 与官方直连两路算出同一值;
   T2 SDE desc 的 a68f1e8d... 与实测字节不符, pkgsrc distinfo 仅确认
   同文件大小 56053928 字节, 无 sha256)
- 构建系统: meson (>= 0.56.0, 上游 0.5.2 起由 autotools 切换至 meson)
- 适配路径: 路径 A (基础适配)
- 申请人: liucu / 队伍: 龙骑士

## 依赖说明

沿用同上游家族 lasem-render 0.5.1 已验证的依赖集合:

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | glib-2.0/gobject-2.0/gio-2.0, 含 glib-mkenums (mkenums 用), shared=True (制品仓仅有此 binary) |
| cairo | 1.18.4 | 渲染后端 (>= 1.2), xlib=disabled 无 X11 链 (同家族 lasem-render 0.5.1 实证; 1.18.4.1 启用 xlib 会引入无 binary 的 libxrender/0.9.12, 其 autotools 在 OHOS 报 C compiler cannot create executables) |
| pango | 1.50.14.1.1 | pangocairo (>= 1.16.0), 文本整形, R37 非 X lineage (pin cairo/1.18.4 + harfbuzz/14.2.0.1.1.1, 绑定 glib shared=True; 1.50.14.1.1.1 会 pin xlib 版 cairo/1.18.4.1 与本包冲突) |
| harfbuzz | 14.2.0.1.1.1 | pango 公开头传递依赖, 消费者需其头文件, R37 共享 glib 版 (旧 14.2.0.1 强制 static glib, 触发无 meson 的源码构建失败) |
| gdk-pixbuf | 2.44.6.1.1 | SVG <image> 像素加载 |
| libxml2 | 2.15.3 | DOM 解析 |
| meson | 1.11.0 | tool_requires, 真机无全局 meson |
| flex | 2.6.4.2 | tool_requires, itex2mml 词法生成 (2.6.4 系仓内仅 OHOS binary，build 机无 binary；改用仅 ConanCenter 有的 2.6.4.2，zimpl 3.7.1 实证) |
| bison | 3.8.2 | tool_requires, itex2mml 语法生成 |
| m4 | 1.4.19 | tool_requires, flex/bison 运行时 exec 的 m4 (flex 二进制硬编码其构建期旧缓存路径，真机不存在即报 fatal internal error code=141；flex 优先读 $M4，build() 经 _ensure_m4_env 指向本包 build 上下文真实 m4；bison 同时需 BISON_PKGDATADIR=<bison包>/share/bison，否则报 /share/bison/m4sugar/m4sugar.m4: cannot open，ball/zimpl/canl-c 同款) |
| gettext | 0.22.5.1 | tool_requires, po/ i18n.gettext 需 xgettext |

meson 选项: wrap_mode=nodownload (依赖一律走 conan),
introspection=disabled / documentation=disabled / viewer=disabled
(gobject-introspection、gi-docgen、gtk4 在 OHOS 不可用)。

## 适配要点

1. glib-mkenums 暴露: conan PkgConfigDeps 只写标准变量, 上游
   gnome.mkenums_simple 经 glib-2.0.pc 的 glib_mkenums 变量定位工具;
   generate() 向生成的 .pc 注入该变量 (pango 1.56.4 同款做法)。
2. llvm-ar 注入: conan MesonToolchain 不把 ar/ranlib 写进 native file,
   meson 按裸名 llvm-ar 探测失败; 由 compiler_executables 的 clang
   同目录推导绝对路径注入 conan_meson_native.ini (cairo 1.18.4 实证)。
3. OHOS XPM 代码签名: build-tree 测试二进制与 .so 在 `meson test`
   前签名 (否则 SIGKILL, exit 137); 安装后的 lib/*.so* 与 bin/
   (lasem-render-0.6 CLI) 在 package() 签名。
4. 只读 /tmp: TMPDIR/TMP/TEMP/HOME/XDG_* 全部指向任务可写 tmp,
   且不用 shell 重定向 (OHOS /bin/sh 在硬编码 /tmp 建临时文件会
   直接 SIGKILL, cairo 1.18.4.2 教训)。
5. 上游测试经 self.run 执行 (tool_requires 的 buildenv PATH 生效;
   裸 subprocess 看不到 conan tool 包的 meson)。
6. itex2mml 生成器 (patches/itex2mml-native.patch): 上游
   find_program('flex'/'bison', required:false) 无 native:true, 缺 flex
   时只在 generator() 报 "Tried to use not-found external program";
   补丁改为 required:true + native:true, 强制走 build 机查找并早失败。
   build() 先将全部 tool_requires bindir 与真机固定工具目录
   (/data/service/hnp/bin 等) 前置到 PATH, 再重注 ini, 不再假设
   generate() 期 PATH 已含工具。

## 上游测试

tests/meson.build 注册 4 个 meson 测试, build() 内 `meson test`
真实执行, 计数唯一来源为 meson 自写的 meson-logs/testlog.txt
汇总块 (Ok:/Expected Fail:/Fail:/Unexpected Pass:/Skipped:/Timeout:),
无 stdout 字符串数数, 无算术修补, 无 returncode 猜测分支:

- dom: DOM API 单元测试, 7 个 g_test_add_func 用例
- str: 字符串工具单元测试, 1 个用例
- filter: SVG filter surface 单元测试, 5 个用例
- suite: 数据驱动渲染回归, 枚举 tests/data 下全部 .svg/.mml
  (排除 ignore-* 前缀、images/ 目录、suite.ini ignore 条目),
  每个文件一个 /render/<path> 子用例, 真实渲染到 cairo surface,
  仅 cairo_status != SUCCESS 时失败 (0.6.0 suite.ini 仅 5 个
  ignore-cairo-status + 4 个 ignore 条目, 均为上游自带声明;
  另经 patches/suite-ini-ignore-image-cases.patch 豁免 6 个图片加载
  用例 tiff.svg/image.svg/svgImageViewBox.svg/svgImageViewBoxClip.svg/
  svgImageViewBoxOverflow.svg/struct-image-05-b.svg: 它们经
  <image xlink:href> 引用 .tif/.svg 资源, 而 conan
  gdk-pixbuf/2.44.6.1.1 只带内建 PNG/JPEG/GIF loader (无 TIFF loader、
  无 librsvg SVG loader), lasem 对 NULL pixbuf 调 g_object_ref 触发
  FATAL-CRITICAL 中断整个 suite; 用上游自带 suite.ini ignore 机制豁免,
  同家族 lasem-render 0.5.1 同款实证, 其余用例全量运行)。

证伪 guard: 汇总绿的前提是 tests/data 下 .svg/.mml 文件数 > 0
且测试二进制非空, 否则判空跑绿失败 (toybox-tar 教训)。

## 验证结果

待真机 evidence 轮填写 (conan create 实测摘录):

- 编译状态: 待验证
- 上游测试用例通过率: 待验证 (目标 4/4 meson 测试)
- 新增测试用例通过率: 待验证 (目标 16/16 断言)

## 已知限制

- viewer (gtk4 实验查看器) 与 introspection/documentation 按上游
  feature 选项显式 disabled, 与 pango/cairo 等 GNOME 系配方一致。
- 产物含 bin/lasem-render-0.6 CLI (上游默认安装), 故软件级附
  commands.json (R38)。
