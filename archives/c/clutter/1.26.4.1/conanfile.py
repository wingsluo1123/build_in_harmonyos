#!/usr/bin/env python3
"""Conan recipe for clutter 1.26.4 — GNOME 场景图库（C）。

clutter（GNOME）是 OpenGL 场景图/交互画布库，autotools 构建。
上游 tag 1.26.4（GNOME Archive，2017-03-09 发布）。

Upstream: https://download.gnome.org/sources/clutter/1.26/clutter-1.26.4.tar.xz

Build:   autotools（tarball 自带 configure/Makefile.in；HMDFS 上须
         touch 全部 Makefile.in 防止 aclocal.m4 重生成——本机无
         aclocal-1.16/autoheader 链；configure 的 confstat 机制
         umask 077 && mktemp 在 HMDFS 上 0700 目录不可写须改
         umask 000——catdoc/boa/ccze/cogl 同款；make -j1：HMDFS
         不支持 jobserver mkfifo）。
         依赖链（制品仓全有）：cogl/1.22.8 + glib/2.84.0.1 +
         pango/1.50.14 + cairo/1.18.4 + atk/2.38.0.1.1 +
         json-glib/1.10.6.1（版本无关，>=0.12 即可；用 1.10.6 因
         json-glib/1.6.6 绑定 glib/2.84.0 与图内 2.84.0.1 冲突）。
         后端：仅启用 generic EGL（--enable-egl-backend，x11/gdk/
         wayland/quartz/win32/mir/cex100/evdev/tslib 全禁——OHOS
         无显示服务与输入子系统）。EGL 经 cogl 封装（libclutter
         NEEDED 无 libEGL，egl 头由系统默认路径解析），无需直连
         egl/gles2 包。
         四大 conan 缓存包适配（cogl 包三缺陷 + cairo 包缺
         cairo-gobject 组件，构建期就地修补）：
         ① cogl 包 .pc 的 prefix 指向构建机残留路径（.cache/
         conan2/p/b/cogl54618945e9137/p）——生成重写版 cogl-1.0.pc/
         cogl-path-1.0.pc 指向 conan 依赖解析的真实 package_folder；
         ② cogl 包 .la 的 libdir/dependency_libs 同样固化残留路径
         （libtool 报 not a valid libtool archive）——正则重写
         .la 内路径；json-glib/atk 包内 .pc 同样 prefix=/ 固化，
         一并重写；
         ③ cogl 包不含 cogl-pango 组件与 cogl-egl.h（上游构建时
         禁用）——clutter 硬依赖 cogl-pango-1.0（CLUTTER_BASE_PC_
         FILES），stub 头+stub 实现源（cogl-pango-stub.c）替代：
         8 个 cogl_pango_* 符号全部为 PangoCairoFontMap 直传或
         GL glyph-cache no-op（OHOS 无显示服务，渲染路径不可达）；
         cogl_egl_context_get_egl_display/context 返回 EGL_NO_*。
         上游测试：conform 83 用例中 17 个纯 CPU 用例（color 5/
         units 3/interval 3/model 5/binding-pool 1）由 test_package
         对安装包实跑（上游 CLUTTER_TEST_SUITE 的 main 经
         clutter_test_init 到 clutter_init 需 EGL 显示服务，不可
         行——顺序调用替代）；其余 66 例涉 stage/GL 渲染/clutter_
         init，OHOS 无显示服务属系统级阻塞（同 cogl 先例口径）。
Install: lib/libclutter-1.0.so* + include/clutter-1.0 + 4 个 .pc
         （clutter-1.0/cally-1.0/clutter-cogl-1.0/clutter-egl-1.0）。
Type:    library（库包——libclutter 供上层 GUI 应用链接）。
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get


class ClutterConan(ConanFile):
    name = "clutter"
    version = "1.26.4.1"
    description = "GNOME scene graph / interactive canvas library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/clutter"
    url = "https://download.gnome.org/sources/clutter/1.26/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # cogl 1.22.8（configure.ac 要求 >=1.21.2 满足）；json-glib 用
    # 1.10.6（版本无关，避免与 glib/2.84.0.1 图冲突）
    requires = ("cogl/1.22.8", "glib/2.84.0.1", "pango/1.50.14",
                "cairo/1.18.4", "atk/2.38.0.1.1", "json-glib/1.10.6.1")
    # cogl 包三缺陷的构建期修补件：cogl-pango stub 头（安装布局
    # cogl-pango/cogl-pango.h + cogl/cogl-egl*.h）与 stub 实现源；
    # cairo 包缺 cairo-gobject 组件的 stub 实现源+stub 头（图内
    # cairo/1.18.4 二进制无 libcairo-gobject.so 与 .pc，CI worker
    # 上连 cairo-gobject.h 头都没有——#66493 实锤，stub 头随配方
    # 提供保证本机/CI 确定性一致）
    exports_sources = ("cogl-pango-stub.c", "cairo-gobject-stub.c",
                       "cairo-gobject.h", "cogl-pango/*", "cogl/*")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        from conan.tools.gnu import PkgConfigDeps
        pcd = PkgConfigDeps(self)
        pcd.generate()

    def build(self):
        src = self.source_folder
        gens = self.generators_folder
        cogl_dir = self.dependencies["cogl"].package_folder
        glib_dir = self.dependencies["glib"].package_folder

        # pkg_config_path：generators_folder（PkgConfigDeps 生成
        # + 下述手写重写版，优先级最高）前置，各依赖包内
        # lib/pkgconfig 兜底（pango 的 pkgconfig 由其配方改写为
        # 真实路径；glib 同理）
        pkg_path = gens
        for dep_name in ("glib", "pango", "atk", "json-glib",
                         "cairo", "cogl"):
            try:
                pc = os.path.join(
                    self.dependencies[dep_name].package_folder,
                    "lib", "pkgconfig")
                if os.path.isdir(pc) and pc not in pkg_path:
                    pkg_path = "%s:%s" % (pkg_path, pc)
            except Exception:
                pass

        # ① 重写固化的 .pc（构建机残留 prefix / prefix=/）：
        #    cogl 系两 pc 按模板重写；cairo-gobject 从 cairo 包内
        #    转发（PkgConfigDeps 只生成主组件）；json-glib/atk 包内
        #    pc prefix=/ 同样重写
        cogl_pc_tpl = (
            "prefix=%s\n"
            "exec_prefix=${prefix}\n"
            "libdir=${exec_prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "apiversion=1.0\n"
            "requires= gobject-2.0 gmodule-no-export-2.0\n"
            "\n"
            "Name: Cogl\n"
            "Description: An object oriented GL/GLES Abstraction/Utility Layer\n"
            "Version: 1.22.8\n"
            "Libs: -L${libdir} -l%s\n"
            "Cflags: -I${includedir}/cogl\n"
            "Requires: ${requires}\n")
        with open(os.path.join(gens, "cogl-1.0.pc"), "w") as f:
            f.write(cogl_pc_tpl % (cogl_dir, "cogl"))
        with open(os.path.join(gens, "cogl-path-1.0.pc"), "w") as f:
            f.write(cogl_pc_tpl % (cogl_dir, "cogl-path"))
        # cogl-pango-1.0.pc：cogl 包无该组件——stub 转发 pc（Libs
        # 直接带 stub 对象文件，链接期闭合 cogl_pango_* 符号）
        with open(os.path.join(gens, "cogl-pango-1.0.pc"), "w") as f:
            f.write(
                "prefix=stub\n"
                "Name: cogl-pango\n"
                "Description: cogl-pango stub (OHOS: cogl built without "
                "cogl-pango)\n"
                "Version: 1.22.8\n"
                "Libs: %s/cogl-pango-stub.o\n"
                "Cflags: -I%s\n"
                "Requires: cogl-1.0 pangocairo\n"
                % (src, src))
        # cairo-gobject.pc：clutter 需要 cairo-gobject >= 1.14——cairo
        #    包二进制完整（.pc+.so+头都在）才转发真实文件；否则 stub
        #    转发 pc（Libs 带 stub 对象文件 + Cflags 指向 src 根的
        #    stub 头——libclutter 实际未解析符号仅 cairo_gobject_
        #    context/surface_get_type 两枚，nm -D 实锤；CI #66493
        #    实锤 worker 的 cairo 包连 cairo-gobject.h 头都没有，
        #    指向 src 保证本机/CI 确定性一致）
        cairo_dir = self.dependencies["cairo"].package_folder
        cg_pc = os.path.join(cairo_dir, "lib", "pkgconfig",
                             "cairo-gobject.pc")
        cg_hdr = os.path.join(cairo_dir, "include", "cairo",
                              "cairo-gobject.h")
        if os.path.isfile(cg_pc) and os.path.isfile(cg_hdr):
            with open(cg_pc, "r", encoding="utf-8",
                      errors="replace") as f:
                cg = f.read()
            cg = cg.replace("prefix=/", "prefix=%s" % cairo_dir)
            with open(os.path.join(gens, "cairo-gobject.pc"), "w") as f:
                f.write(cg)
        else:
            # Cflags 指向 src 根（stub 头 cairo-gobject.h 由
            # exports_sources 解到源码根——worker 的 cairo 包连头都
            # 没有，指向 src 保证本机/CI 确定性一致）
            with open(os.path.join(gens, "cairo-gobject.pc"), "w") as f:
                f.write(
                    "prefix=stub\n"
                    "Name: cairo-gobject\n"
                    "Description: cairo-gobject stub (OHOS: cairo pkg "
                    "binary without cairo-gobject component)\n"
                    "Version: 1.18.4\n"
                    "Libs: %s/cairo-gobject-stub.o\n"
                    "Cflags: -I%s\n"
                    "Requires: cairo gobject-2.0\n"
                    % (src, src))
        # json-glib-1.0.pc / atk.pc：包内 pc prefix=/ 固化——按包
        # 布局重写（json-glib 头在 include/json-glib-1.0；atk 头在
        # include/atk-1.0 + include）
        jg_dir = self.dependencies["json-glib"].package_folder
        with open(os.path.join(gens, "json-glib-1.0.pc"), "w") as f:
            f.write(
                "prefix=%s\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include/json-glib-1.0\n"
                "\n"
                "Name: Json-GLib\n"
                "Description: JSON-GLib - JSON parser for GLib\n"
                "Version: 1.10.6\n"
                "Libs: -L${libdir} -ljson-glib-1.0\n"
                "Cflags: -I${includedir}\n"
                "Requires: gobject-2.0\n" % jg_dir)
        atk_dir = self.dependencies["atk"].package_folder
        with open(os.path.join(gens, "atk.pc"), "w") as f:
            f.write(
                "prefix=%s\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include/atk-1.0\n"
                "includedir1=${prefix}/include\n"
                "\n"
                "Name: atk\n"
                "Description: atk (accessibility toolkit)\n"
                "Version: 2.38.0.1.1\n"
                "Libs: -L${libdir} -latk-1.0 -lm -lpthread -ldl\n"
                "Cflags: -I${includedir} -I${includedir1}\n"
                "Requires: glib-2.0 gobject-2.0\n" % atk_dir)

        # ② 修 cogl 包 .la：libdir/dependency_libs 固化原构建机
        #    conan home 路径（libtool 报 not a valid libtool archive，
        #    CI #66619 实锤：libtool 解析 dependency_libs 引用的 .la
        #    路径报 not found——正则只覆盖 -L/libdir 形态不够）。全量
        #    重建为最小合法 .la：dlname/library_names 按包内真实
        #    .so 文件名生成、dependency_libs 置空、libdir 指向当前
        #    包（.la 是构建期中间产物，链接语义由 -L/-l 与 .so 本身
        #    保证——本机缓存包 .la 可能被早前轮次就地修补而"碰巧"
        #    通过，CI 全新环境必暴露，重建后本机/CI 确定性一致）
        for la_name in ("libcogl.la", "libcogl-path.la",
                        "libcogl-gles2.la"):
            la_path = os.path.join(cogl_dir, "lib", la_name)
            if not os.path.isfile(la_path):
                continue
            lib = la_name[:-3]
            so_files = [fn for fn in os.listdir(
                os.path.join(cogl_dir, "lib"))
                if fn.startswith(lib + ".so.")]
            if not so_files:
                continue
            # soname（.so.N）与完整文件名（.so.N.M.R）——按包内实际
            # 文件构造，不猜版本号
            full = sorted(so_files, key=len)[-1]
            soname = None
            for fn in so_files:
                parts = fn.split(".so.")
                if len(parts) == 2 and len(parts[1].split(".")) == 1:
                    soname = fn
            soname = soname or full
            with open(la_path, "w") as f:
                f.write(
                    "# %s - a libtool library file\n"
                    "# Generated by ltmain.sh (GNU libtool) 2.4.6\n"
                    "# (rebuilt by clutter recipe: OHOS conan pkg .la "
                    "baked build-machine paths)\n"
                    "dlname='%s'\n"
                    "library_names='%s %s'\n"
                    "old_library=''\n"
                    "dependency_libs=''\n"
                    "current=20\nage=4\nrevision=3\n"
                    "installed=yes\nshouldnotlink=no\n"
                    "dlopen=''\ndlpreopen=''\n"
                    "libdir='%s/lib'\n"
                    % (la_name, soname, full, soname, cogl_dir))

        # ③ 编译 cogl-pango stub（头文件已由 exports_sources
        #    随 conanfile 解到源码根：cogl-pango/cogl-pango.h +
        #    cogl/cogl-egl.h；实现源 cogl-pango-stub.c 同目录）
        stub_c = os.path.join(src, "cogl-pango-stub.c")
        if not os.path.isfile(stub_c):
            raise Exception("cogl-pango-stub.c missing (exports_sources)")
        cc = "/data/service/hnp/bin/clang"
        # export 而非 env 前缀：shell 先做反引号命令替换再执行 env
        # 前缀——替换子 shell 看不到 env 前缀设的 PKG_CONFIG_PATH
        # （实测 pkg-config 报 not found → glib-object.h 缺失）
        self.run(
            "export PKG_CONFIG_PATH=%s; %s -c %s -o %s/cogl-pango-stub.o "
            "-I%s -DCOGL_HAS_EGL_SUPPORT=1 -fPIC -O2 "
            "`pkg-config --cflags glib-2.0 gobject-2.0 pangocairo "
            "cogl-1.0`"
            % (pkg_path, cc, stub_c, src, src), env="conanbuild")

        # ④ 编译 cairo-gobject stub（cairo 包二进制缺该组件时——
        #    cairo-gobject.pc 已按 stub 转发，Libs 带本 .o 链接期
        #    闭合 cairo_gobject_context/surface_get_type 两符号）
        if not os.path.isfile(os.path.join(cairo_dir, "lib",
                                           "libcairo-gobject.so")):
            stub_cg = os.path.join(src, "cairo-gobject-stub.c")
            if not os.path.isfile(stub_cg):
                raise Exception("cairo-gobject-stub.c missing "
                                "(exports_sources)")
            self.run(
                "export PKG_CONFIG_PATH=%s; %s -c %s "
                "-o %s/cairo-gobject-stub.o -fPIC -O2 "
                "`pkg-config --cflags cairo gobject-2.0`"
                % (pkg_path, cc, stub_cg, src), env="conanbuild")

        # configure 补丁：confstat 机制（umask 077 && mktemp -d）
        #    创建 0700 临时目录——OHOS HMDFS 上 0700 目录不可写
        #    （subs1.awk Permission denied，catdoc/boa/ccze/cogl
        #    同款）——改 umask 000
        cfs = os.path.join(src, "configure")
        with open(cfs, "r", encoding="utf-8", errors="replace") as f:
            cs = f.read()
        cs2 = cs.replace('(umask 077 &&', '(umask 000 &&')
        if cs2 != cs:
            with open(cfs, "w") as f:
                f.write(cs2)

        # HMDFS：touch 关键 autotools 文件防 make 触发重生成（本机
        #    无 aclocal-1.16/automake/autoconf 链）。用固定递增时间
        #    戳分四层排序：源层（configure.ac + 全部 Makefile.am/
        #    .m4）< aclocal.m4 < 中间层（Makefile.in/config.h.in）<
        #    configure——乱序 touch 或亚秒 mtime 会让某文件显 stale
        #    触发重生成（实测两次：aclocal.m4 stale → aclocal
        #    Error 127；Makefile.in stale → automake Error 1）
        import time
        base_t = int(time.time()) - 3600
        layers = (
            (1, ("configure.ac",), (".am", ".m4")),
            (2, ("aclocal.m4",), ()),
            (3, ("Makefile.in", "config.h.in"), ()),
            (4, ("configure",), ()),
        )
        for offset, exact_names, suffixes in layers:
            for root, dirs, files in os.walk(src):
                for fn in files:
                    hit = any(fn == n for n in exact_names)
                    if not hit:
                        hit = any(fn.endswith(s) and fn != "aclocal.m4"
                                  for s in suffixes)
                    if hit:
                        p = os.path.join(root, fn)
                        try:
                            t = base_t + offset
                            os.utime(p, (t, t))
                        except OSError:
                            pass

        # configure：仅 EGL 后端 + 全禁显示/输入后端；glib 运行
        #    时测试跳过（AM_PATH_GLIB_2_0 测试程序跑不起来——
        #    LD_LIBRARY_PATH 已注入仍读垃圾版本，cogl 同款）；
        #    GLIB 工具环境变量注入
        gbin = os.path.join(glib_dir, "bin")
        lib_dirs = []
        for dep_name in ("cogl", "glib", "pango", "cairo", "atk",
                         "json-glib"):
            try:
                libd = os.path.join(
                    self.dependencies[dep_name].package_folder, "lib")
                if os.path.isdir(libd):
                    lib_dirs.append(libd)
            except Exception:
                pass
        ld_path = ":".join(lib_dirs)
        cflags = ("-DCOGL_HAS_EGL_SUPPORT=1 -fPIC -O2 "
                  "-Wno-error=implicit-function-declaration -Wno-error")
        self.run(
            "env PKG_CONFIG_PATH=%s LD_LIBRARY_PATH=%s "
            "GLIB_MKENUMS=%s/glib-mkenums GLIB_GENMARSHAL=%s/"
            "glib-genmarshal GOBJECT_QUERY=%s/gobject-query "
            "GLIB_COMPILE_RESOURCES=%s/glib-compile-resources "
            "./configure --prefix=%s "
            "--disable-glibtest "
            "--disable-gtk-doc --disable-introspection --disable-docs "
            "--disable-examples "
            "--disable-x11-backend --disable-gdk-backend "
            "--disable-wayland-backend --disable-quartz-backend "
            "--disable-win32-backend --disable-mir-backend "
            "--disable-cex100-backend --disable-evdev-input "
            "--disable-tslib-input --enable-egl-backend "
            "--disable-gdk-pixbuf --enable-debug=no --disable-Bsymbolic "
            "CFLAGS='%s' CC=%s "
            "--build=aarch64-unknown-linux-gnu "
            "--host=aarch64-unknown-linux-gnu"
            % (pkg_path, ld_path, gbin, gbin, gbin, gbin,
               self.package_folder, cflags, cc), env="conanbuild")

        # SUBDIRS 裁剪：顶层 Makefile 的 tests（conform 链接需
        #    GL 渲染环境且缺 test_utils_* 符号）/doc（gtk-doc）/
        #    po（gettext）从构建树移除——主库构建不受影响；上游
        #    测试的实跑改由 test_package 对安装包进行
        topmk = os.path.join(src, "Makefile")
        with open(topmk, "r", encoding="utf-8", errors="replace") as f:
            sm = f.read()
        sm2 = sm.replace(
            "SUBDIRS = build-aux clutter tests doc po $(am__append_1)",
            "SUBDIRS = build-aux clutter $(am__append_1)")
        if sm2 != sm:
            with open(topmk, "w") as f:
                f.write(sm2)

        # make -j1：HMDFS 不支持 jobserver mkfifo（Operation not
        # permitted）
        self.run("make -j1", env="conanbuild")

    def package(self):
        # build 完成后拷产物：make install 按 configure --prefix 直接
        # 落盘 package_folder（lib + include/clutter-1.0 +
        # lib/pkgconfig）；随后校验核心产物齐备（主 so/主头/4 个
        # .pc）——缺任一即 Exception，不产出残缺包
        self.run("make install", env="conanbuild")
        pkg = self.package_folder
        missing = []
        if not os.path.isfile(os.path.join(
                pkg, "lib", "libclutter-1.0.so")):
            missing.append("lib/libclutter-1.0.so")
        if not os.path.isfile(os.path.join(
                pkg, "include", "clutter-1.0", "clutter", "clutter.h")):
            missing.append("include/clutter-1.0/clutter/clutter.h")
        for pc in ("clutter-1.0.pc", "cally-1.0.pc",
                   "clutter-cogl-1.0.pc", "clutter-egl-1.0.pc"):
            if not os.path.isfile(os.path.join(
                    pkg, "lib", "pkgconfig", pc)):
                missing.append("lib/pkgconfig/" + pc)
        if missing:
            raise Exception("package() 产物校验失败，缺失：%s"
                            % ", ".join(missing))
        self.output.info("package() 产物校验通过：libclutter-1.0.so + "
                         "clutter.h + 4 个 .pc")

    def test(self):
        # 上游测试真跑（R34/L0c 口径，self.run 实跑）：编译并运行
        # consumer.c + 上游纯 CPU 子集 17 用例（color 5/units 3/
        # interval 3/model 5/binding-pool 1——~/tmp/clutter-tp 已验证
        # 同款），对安装包 self.package_folder 进行。复用 test_package/
        # test_clutter.py（编译链接运行一体），依赖 include/libdirs 全
        # 链收集注入环境变量（与 test_package 同款三点版本无关性
        # 保证：按名索引防 Dependencies 迭代协议不一致、
        # aggregated_components 聚合组件 include、包内头子目录补齐）。
        # LD_LIBRARY_PATH 前置 /system/lib64（OHOS libc++ 唯一真 so
        # 所在；SDK libc++.so 是链接器脚本，direct run 加载器不认）。
        # 注：conan create 的缓存导出上下文中 test_package/ 不随主配方
        # 导出（独立 test_package recipe）——该场景上游测试真跑由
        # create 的 test_package 阶段执行（同一 17 用例同一脚本），
        # 此处如实降级说明，不静默假装通过。
        script = os.path.join(self.recipe_folder, "test_package",
                              "test_clutter.py")
        if not os.path.isfile(script):
            self.output.info(
                "test(): recipe_folder 无 test_package/test_clutter.py"
                "（conan 缓存导出上下文）——上游测试真跑由 conan create"
                " 的 test_package 阶段执行（同 17 用例），此处跳过")
            return
        dep_names = ("cogl", "glib", "pango", "cairo", "atk",
                     "json-glib", "fribidi", "harfbuzz", "libffi",
                     "pcre2", "zlib", "expat", "fontconfig",
                     "freetype", "libpng", "pixman", "pixman-1")
        dep_incs = []
        dep_libdirs = []
        for dep_name in dep_names:
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            try:
                agg = dep.cpp_info.aggregated_components()
                incs = list(agg.includedirs)
                libds = list(agg.libdirs)
            except Exception:
                incs = list(dep.cpp_info.includedirs)
                libds = list(dep.cpp_info.libdirs)
            for inc in incs:
                if inc not in dep_incs:
                    dep_incs.append(inc)
            for libd in libds:
                if libd not in dep_libdirs:
                    dep_libdirs.append(libd)
        for dep_name, subs in (("cairo", ("cairo",)),
                               ("cogl", ("cogl",)),
                               ("json-glib", ("json-glib-1.0",)),
                               ("atk", ("atk-1.0",))):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            for sub in subs:
                d = os.path.join(dep.package_folder, "include", sub)
                if os.path.isdir(d) and d not in dep_incs:
                    dep_incs.append(d)
        os.environ["CLUTTER_TEST_DEP_INCLUDES"] = " ".join(dep_incs)
        os.environ["CLUTTER_TEST_DEP_LIBDIRS"] = " ".join(dep_libdirs)
        from conan.tools.env import Environment
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        self.run('python3 "%s" "%s"' % (script, self.package_folder),
                 env=env)

    def package_info(self):
        self.output.info("clutter 1.26.4: libclutter-1.0")
