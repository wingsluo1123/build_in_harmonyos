#!/usr/bin/env python3
"""Conan recipe — gnome-desktop 44.1 (Meson, GNOME desktop utility library).

gnome-desktop 提供 GNOME 桌面组件共用的工具库：壁纸/幻灯片背景（gnome-bg）、
语言/区域匹配（gnome-languages，ISO-639/3166 + 本地化语言名）、显示器布局
（gnome-rr，经 Mutter DisplayConfig D-Bus）、缩略图工厂（gnome-desktop-thumbnail，
含 thumbnailer 沙箱脚本执行）、XKB 布局信息（gnome-xkb-info）、空闲监视
（gnome-idle-monitor）、PNP ID 解码与壁钟格式化（gnome-wall-clock）。

构建系统：Meson（上游 meson.build，选项按上游语义映射）
上游测试：tests/ 下 4 个 GLib g_test 程序（bg-slide-show / wall-clock /
          wallclock-reftest / languages，共 12 个用例）。上游 meson.build
          故意不注册 test()（注释说明依赖已安装的 locale 数据），因此测试
          二进制编译后手动执行 —— 见 notes.md 实测表。
          libgnome-desktop/test-*.c 是交互式调试工具，无 g_test 用例。

OHOS 适配要点（实测结论，详见 notes.md）：
  - 目标库：libgnome-desktop-3（legacy，gtk3 体系）为默认构建；
    build_gtk4 路径（libgnome-desktop-4 / gnome-bg-4 / gnome-rr-4）默认关闭。
  - 制品仓 W0 实测：gtk/3.24.43 与 gtk4/4.22.4 分属两套 pango pin
    （1.50.14.1.1 / 1.56.4），同一依赖图内并存会触发 pango 版本冲突；
    统一 override 后 gtk/3.24.43 二进制 package_id 变化 → 制品仓无对应
    binary（W0 证据：conan install --build=never 报 Missing binary）。
    故按 R36 只消费已发布 binary：legacy(gtk3) 路径 27 个依赖节点全部
    Cache/Download 命中，build_gtk4 需待 gtk3+gtk4 统一 pin 的依赖先行发布。
  - seccomp/bwrap 沙箱：上游仅在 host_os == 'linux' 时探测 libseccomp；
    OHOS 的 meson host system 为 harmonyos → ENABLE_SECCOMP/HAVE_BWRAP=0，
    thumbnailer 沙箱降级（沙箱脚本仍可用，无 seccomp 过滤）。
  - HAVE_SYSTEMD=0（无 systemd 依赖），HAVE_UDEV 由可选的 libudev 决定。
  - glib 构建工具（glib-mkenums/gdbus-codegen 为 Python 脚本，
    glib-compile-resources/glib-compile-schemas/gio-querymodules 为 ELF）
    由 generate() 落到构建目录私有目录，ELF 在 OHOS 上补签名后执行。
  - 字体缓存路径（FONTCONFIG_CACHE_PATH）仅用于 bwrap 沙箱内 ro-bind，
    沙箱关闭后不影响运行；仍从 fontconfig 依赖注入以满足 meson 变量查询。
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GnomeDesktopConan(ConanFile):
    name = "gnome-desktop"
    version = "44.1"
    description = ("GNOME desktop utility library — wallpaper/slide-show, "
                   "locale matching, XKB info, thumbnail factory, wall clock")
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-desktop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_gtk4": [True, False],
        "legacy_library": [True, False],
        "with_introspection": [True, False],
        "debug_tools": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        # libgnome-desktop-3（gtk3）默认开启：上游 tests/ 全部依赖它，
        # 且该路径依赖图在 ohpcd 100% 可消费（W0 实测）。
        "build_gtk4": False,
        "legacy_library": True,
        "with_introspection": False,
        # 上游默认安装 libexec/gnome-desktop-debug 下的交互式调试程序
        # （test-* / gnome-rr-debug）。库包默认不装：这些是手工调试工具，
        # 非库 API；需要时 -o debug_tools=True。
        "debug_tools": False,
        # 上游测试需已安装的 locale 数据与 schema；默认不随包构建执行，
        # 本地/CI 可用 -o with_tests=True 打开（见 build()）。
        "with_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # ohpcd 上 glib/gdk-pixbuf/gtk 只发布 shared=True 的 OHOS binary
        # （W0：conan download 后 conan install --build=never 全命中）。
        for dep, opt in (("glib", "shared"), ("gdk-pixbuf", "shared"),
                         ("gtk", "shared"), ("pango", "shared"),
                         ("cairo", "shared"), ("cairo-gobject", "shared"),
                         ("atk", "shared"), ("harfbuzz", "shared")):
            try:
                setattr(self.options[dep], opt, True)
            except Exception:
                pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if not (self.options.build_gtk4 or self.options.legacy_library):
            raise ConanInvalidConfiguration(
                "Both build_gtk4 and legacy_library are disabled — nothing to build")
        if self.options.build_gtk4 and self.options.legacy_library:
            # W0 实测（R36）：gtk/3.24.43 pin pango/1.50.14.1.1，
            # gtk4/4.22.4 pin pango/1.56.4。统一 override 后 gtk/3.24.43
            # 的 package_id 变化，ohpcd 无对应 binary（Missing binary）。
            # 依赖未发布前不允许图内并存，避免 --build=missing 隐性编译依赖。
            raise ConanInvalidConfiguration(
                "build_gtk4=True together with legacy_library=True is not "
                "consumable yet: gtk/3.24.43 (pango/1.50.14.1.1) and "
                "gtk4/4.22.4 (pango/1.56.4) pin different pango versions and "
                "no gtk3 binary exists for the unified override graph. "
                "Use -o legacy_library=True -o build_gtk4=False (default) or "
                "wait for unified dependency publication (R36).")

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        # gnome-desktop-3.0（legacy）与 gnome-desktop-4.0 的公共部分
        self.requires("gsettings-desktop-schemas/49.1", transitive_headers=True)
        self.requires("xkeyboard-config/2.48")
        self.requires("iso-codes/4.20.1")
        self.requires("fontconfig/2.18.1.1", transitive_headers=True,
                      transitive_libs=True)
        if self.options.legacy_library:
            # pkg-config: gtk+-3.0 / gdk-pixbuf-2.0 / glib-2.0 / gio-2.0 /
            # gio-unix-2.0。版本取 ohpcd 中已发布 OHOS binary 的组合。
            self.requires("glib/2.84.0.1", transitive_headers=True,
                          transitive_libs=True)
            self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True,
                          transitive_libs=True)
            self.requires("gtk/3.24.43", transitive_headers=True,
                          transitive_libs=True)
        else:
            # build_gtk4 路径（当前制品仓缺 pango/harfbuzz 组合 binary，
            # 需依赖先发布；保留上游语义以便发布后直接启用）
            self.requires("glib/2.84.0.1", transitive_headers=True,
                          transitive_libs=True)
            self.requires("gdk-pixbuf/2.44.6", transitive_headers=True,
                          transitive_libs=True)
            self.requires("gtk4/4.22.4", transitive_headers=True,
                          transitive_libs=True)

    def build_requirements(self):
        # meson 由 tool_requires 提供（CI/本机均无系统 meson）
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── generate ────────────────────────────────────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_gio_unix_pc()
        self._create_xkeyboard_config_pc()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        self._fix_fontconfig_pc()
        self._sync_cairo_headers_from_gobject()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "desktop_docs": "false",
            "debug_tools": "true" if self.options.debug_tools else "false",
            "introspection": "true" if self.options.with_introspection else "false",
            "gtk_doc": "false",
            "installed_tests": "false",
            "build_gtk4": "true" if self.options.build_gtk4 else "false",
            "legacy_library": "true" if self.options.legacy_library else "false",
            "systemd": "disabled",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    # ── build ───────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if self.options.with_tests:
                self._run_upstream_tests()

    def _run_upstream_tests(self):
        """运行上游 tests/ 的 4 个 g_test 程序（共 12 个用例）。

        上游 meson.build 不注册 test()，二进制编译后手动执行：
          bg-slide-show(2) / wall-clock(5) / wallclock-reftest(4) / languages(1)
        需要 G_TEST_SRCDIR 指向源码 tests/，GSETTINGS_SCHEMA_DIR 指向
        已编译的 gsettings-desktop-schemas（上游注释明确测试依赖已安装数据）。
        """
        test_dir = os.path.join(self.build_folder, "tests")
        if not os.path.isdir(test_dir):
            self.output.warning("tests/ build dir missing — legacy_library disabled?")
            return
        # HarmonyOS 执行 ELF 需要签名：构建目录内的库与被测程序都要签
        self._sign_build_artifacts()
        schemas = self._compiled_schemas_dir()
        env = Environment()
        env.define_path("G_TEST_SRCDIR", os.path.join(self.source_folder, "tests"))
        env.define_path("G_TEST_BUILDDIR", test_dir)
        if schemas:
            env.define_path("GSETTINGS_SCHEMA_DIR", schemas)
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                if os.path.isdir(path):
                    env.prepend_path("LD_LIBRARY_PATH", path)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder,
                                                         "libgnome-desktop"))
        with env.vars(self).apply():
            for program in ("bg-slide-show", "wall-clock", "wallclock-reftest",
                            "languages"):
                binary = os.path.join(test_dir, program)
                if not os.path.isfile(binary):
                    raise ConanException(f"upstream test binary missing: {binary}")
                self.run(shlex.quote(binary), env="conanbuild")

    def _compiled_schemas_dir(self):
        """把依赖 gsettings-desktop-schemas 的 XML schema 编译到构建目录。

        制品仓 gsettings-desktop-schemas 包内只有 XML，无 gschemas.compiled；
        上游测试（wall-clock）需要 schema 才能创建 GSettings 对象。
        """
        try:
            schemas_pkg = self.dependencies["gsettings-desktop-schemas"].package_folder
        except KeyError:
            return None
        src = os.path.join(schemas_pkg, "share", "glib-2.0", "schemas")
        if not os.path.isdir(src):
            return None
        out = os.path.join(self.build_folder, "glib-schemas")
        os.makedirs(out, exist_ok=True)
        for xml in glob.glob(os.path.join(src, "*.xml")):
            shutil.copy2(xml, os.path.join(out, os.path.basename(xml)))
        compiler = os.path.join(self._glib_tools_folder(), "glib-compile-schemas")
        if not os.path.isfile(compiler):
            compiler = os.path.join(self.dependencies["glib"].package_folder, "bin",
                                    "glib-compile-schemas")
        if os.path.isfile(compiler):
            self.run(f"{shlex.quote(compiler)} {shlex.quote(out)}", env="conanbuild")
        return out

    # ── package ─────────────────────────────────────────────────────────
    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        rm(self, "*.la", self.package_folder)
        self._sanitize_pc_files()
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gnome-desktop-3"]
        self.cpp_info.includedirs = ["include/gnome-desktop-3.0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "gnome-desktop-3.0")
        self.cpp_info.set_property("cmake_target_name",
                                   "gnome-desktop-3.0::gnome-desktop-3.0")
        self.cpp_info.set_property("pkg_config_name", "gnome-desktop-3.0")
        # 公开头文件引用 gtk/gdk-pixbuf/glib/gio/gsettings 类型，必须传播
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "gtk::gtk",
            "gdk-pixbuf::gdk-pixbuf",
            "fontconfig::fontconfig",
            "gsettings-desktop-schemas::gsettings-desktop-schemas",
            # 数据类直接依赖（运行时数据：iso-codes XML/locale、
            # xkeyboard-config 规则），无编译产物但必须声明（conan 要求
            # 每个 direct require 出现在 cpp_info.requires 中）
            "iso-codes::iso-codes",
            "xkeyboard-config::xkeyboard-config",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── glib build tools ────────────────────────────────────────────────
    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        # Python 脚本型工具：wrapper 用绝对路径调解释器，避免生成 ELF
        for tool in ("glib-genmarshal", "glib-mkenums", "gdbus-codegen"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            self._build_python_tool_wrapper(tool, src)
        # ELF 工具：复制并按需签名后使用
        for tool in ("glib-compile-resources", "glib-compile-schemas",
                     "gio-querymodules", "gobject-query"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            dst = os.path.join(tools_folder, tool)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(dst)
        return tools_folder

    def _build_python_tool_wrapper(self, name, script):
        tools_folder = self._glib_tools_folder()
        wrapper = os.path.join(tools_folder, name)
        python = os.path.realpath(sys.executable)
        quote = lambda s: "'" + str(s).replace("'", "'\\''") + "'"  # noqa: E731
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\nexec {} {} \"$@\"\n".format(
                quote(python), quote(script)))
        os.chmod(wrapper, 0o755)

    def _augment_glib_pkg_config(self, tools_folder):
        """向 PkgConfigDeps 生成的 glib/gio .pc 注入 meson gnome 模块所需变量。

        PkgConfigDeps 只输出 libs/cflags，丢失 meson 的
          gnome.gdbus_codegen → gio-2.0.pc:gdbus_codegen
          gnome.mkenums → glib-2.0.pc:glib_mkenums
          gnome.compile_schemas/resources → glib_compile_* / gio_querymodules
        变量缺失时 meson 报 'Could not get pkg-config variable'。
        """
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")
        # glib 2.84.0.1 的 OHOS 制品把 libintl 打进 glib 包并做符号改名
        # （g_libintl_*），而 PkgConfigDeps 生成的 .pc 丢掉了 -lintl →
        # 链接 libgnome-desktop 时报 undefined symbol: g_libintl_dgettext。
        # 这里按包内真实存在的 libintl 补回 -lintl。
        glib_libdir = os.path.join(self.dependencies["glib"].package_folder, "lib")
        need_intl = any(os.path.isfile(os.path.join(glib_libdir, name))
                        for name in ("libintl.so", "libintl.a"))
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc"):
            pc_path = os.path.join(self.generators_folder, pc_name)
            if not need_intl or not os.path.isfile(pc_path):
                continue
            text = open(pc_path, encoding="utf-8").read()
            out = []
            for line in text.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                out.append(line)
            open(pc_path, "w", encoding="utf-8", newline="\n").write("".join(out))
        variables = {
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            "gobject_query": os.path.join(tools_folder, "gobject-query"),
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        content = open(glib_pc, encoding="utf-8").read()
        block = "".join(
            f"{key}={value.replace(os.sep, '/')}\n" for key, value in variables.items()
            if f"{key}=" not in content)
        if block:
            content = content.replace("\nName:", f"\n{block}\nName:", 1)
            open(glib_pc, "w", encoding="utf-8", newline="\n").write(content)
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            gio_vars = {
                "gdbus_codegen": os.path.join(tools_folder, "gdbus-codegen"),
                "glib_compile_schemas": os.path.join(tools_folder,
                                                     "glib-compile-schemas"),
                "glib_compile_resources": os.path.join(tools_folder,
                                                       "glib-compile-resources"),
                "gio_querymodules": os.path.join(tools_folder, "gio-querymodules"),
            }
            content = open(gio_pc, encoding="utf-8").read()
            block = "".join(
                f"{key}={value.replace(os.sep, '/')}\n"
                for key, value in gio_vars.items() if f"{key}=" not in content)
            if block:
                content = content.replace("\nName:", f"\n{block}\nName:", 1)
                open(gio_pc, "w", encoding="utf-8", newline="\n").write(content)

    def _create_gio_unix_pc(self):
        """生成 gio-unix-2.0.pc（别名）。

        上游 meson.build 需要 dependency('gio-unix-2.0')，而 glib 配方未声明
        gio-unix-2.0 组件，PkgConfigDeps 不会产出该 .pc；MesonToolchain 的
        pkg_config_path 只指向 conan 生成目录（不看 PKG_CONFIG_PATH 环境），
        所以必须在生成目录内造别名。gio-2.0.pc 的 Cflags 已包含
        include/gio-unix-2.0，直接复用即可。
        """
        src = os.path.join(self.generators_folder, "gio-2.0.pc")
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        if not os.path.isfile(src) or os.path.isfile(dst):
            return
        content = open(src, encoding="utf-8").read()
        content = content.replace("Name: gio-2.0", "Name: gio-unix-2.0", 1)
        open(dst, "w", encoding="utf-8", newline="\n").write(content)

    def _create_xkeyboard_config_pc(self):
        """生成上游 meson 需要的 xkeyboard-config.pc 并给出可用的 xkb_base。

        xkeyboard-config 包内的 xkeyboard-config-2.pc 里
        xkb_base=${datadir}/X11/xkb，而包内 share/X11/xkb 是绝对软链
        -> /share/xkeyboard-config-2（脱离包前缀，指向不存在路径）。
        XKB_BASE 会被编译进 libgnome-desktop（gnome-xkb-info.c 读
        XKB_CONFIG_ROOT 或 XKB_BASE），因此这里指向包内真实数据目录
        share/xkeyboard-config-2。
        """
        dst = os.path.join(self.generators_folder, "xkeyboard-config.pc")
        if os.path.isfile(dst):
            return
        try:
            pkg = self.dependencies["xkeyboard-config"].package_folder
        except KeyError:
            return
        data = os.path.join(pkg, "share", "xkeyboard-config-2")
        if not os.path.isdir(data):
            data = os.path.join(pkg, "share", "X11", "xkb")
        data = data.replace(os.sep, "/")
        content = (
            f"prefix={pkg.replace(os.sep, '/')}/share\n"
            "exec_prefix=${prefix}\n"
            "datarootdir=${prefix}\n"
            "datadir=${prefix}\n"
            f"xkb_base={data}\n\n"
            "Name: XKeyboardConfig\n"
            "Description: X Keyboard Configuration data\n"
            f"Version: {self.dependencies['xkeyboard-config'].ref.version}\n"
        )
        open(dst, "w", encoding="utf-8", newline="\n").write(content)

    def _fix_fontconfig_pc(self):
        """补齐 fontconfig.pc 的 cachedir 变量。

        上游 meson.build 读取 fontconfig_dep.get_variable(pkgconfig:'cachedir')，
        而 PkgConfigDeps 生成物无该变量 → configure 失败。注入依赖包内路径；
        该宏仅用于 bwrap 沙箱 ro-bind（OHOS 上沙箱关闭，运行期不读）。
        """
        pc = os.path.join(self.generators_folder, "fontconfig.pc")
        if not os.path.isfile(pc):
            return
        content = open(pc, encoding="utf-8").read()
        if "cachedir=" in content:
            return
        try:
            pkg = self.dependencies["fontconfig"].package_folder
        except KeyError:
            return
        cache = os.path.join(pkg, "var", "cache", "fontconfig").replace(os.sep, "/")
        content = content.replace("\nName:", f"\ncachedir={cache}\n\nName:", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)

    def _sync_cairo_headers_from_gobject(self):
        """cairo 与 cairo-gobject 两个包都带 include/cairo/*.h。

        cairo-features.h 内容不同（cairo-gobject 启用 CAIRO_HAS_GOBJECT_FUNCTIONS），
        命令行命中哪份取决于聚合顺序；统一用 cairo-gobject（超集）覆盖 cairo
        包头文件目录，使头集合与顺序无关（gtk 配方已实证的必要修复）。
        """
        try:
            gobject_pkg = self.dependencies["cairo-gobject"]
            cairo_pkg = self.dependencies["cairo"]
        except KeyError:
            return

        def first_include(dep):
            for item in dep.cpp_info.includedirs:
                path = item if os.path.isabs(item) else os.path.join(
                    dep.package_folder, item)
                if os.path.isdir(path):
                    return path
            return None

        src = first_include(gobject_pkg)
        dst = first_include(cairo_pkg)
        if not src or not dst or src == dst:
            return
        copied = 0
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            out = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(out, exist_ok=True)
            for name in files:
                shutil.copy2(os.path.join(root, name), os.path.join(out, name))
                copied += 1
        if copied:
            self.output.info(f"synced {copied} cairo headers from cairo-gobject")

    def _inject_meson_tools(self, tools_folder):
        """向 meson machine 文件补 ar/ranlib/pkg-config/glib-compile-resources。

        MesonToolchain 只写 cc/cpp；OHOS 上 llvm-ar 等不在 PATH，meson 探测
        裸名会失败。
        """
        compiler_exec = self.conf.get("tools.build:compiler_executables",
                                     default={}, check_type=dict) or {}
        cc = compiler_exec.get("c") or ""
        cc_dir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compiler_exec.get("ar")
        ranlib = compiler_exec.get("ranlib")
        if cc_dir:
            if not ar:
                candidate = os.path.join(cc_dir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(cc_dir, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
            if not pkg_config and cc_dir:
                candidate = os.path.join(cc_dir, "pkg-config")
                if os.path.isfile(candidate):
                    pkg_config = candidate
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine):
                continue
            content = open(machine, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            extra = []
            if ar and "\nar =" not in content:
                extra.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                extra.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content \
                    and "\npkgconfig =" not in content:
                extra.append(f"pkg-config = '{pkg_config}'")
            gcr = os.path.join(tools_folder, "glib-compile-resources")
            if os.path.isfile(gcr) and "\nglib-compile-resources =" not in content:
                extra.append(f"glib-compile-resources = '{gcr}'")
            if not extra:
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n" + "\n".join(extra) + "\n", 1)
            open(machine, "w", encoding="utf-8", newline="\n").write(content)

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        glib_folder = self.dependencies["glib"].package_folder
        env.prepend_path("PATH", os.path.join(glib_folder, "bin"))
        env.prepend_path("PATH", self._glib_tools_folder())
        # PkgConfigDeps 生成目录 + 依赖自带 .pc 目录（xkeyboard-config.pc、
        # iso-codes.pc 装在 share/pkgconfig）
        pkg_config_paths = [self.generators_folder]
        for dep in self.dependencies.host.values():
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                candidate = os.path.join(dep.package_folder, sub)
                if os.path.isdir(candidate):
                    pkg_config_paths.append(candidate)
        for path in pkg_config_paths:
            env.prepend_path("PKG_CONFIG_PATH", path)
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                if os.path.isdir(path):
                    env.prepend_path("LD_LIBRARY_PATH", path)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder,
                                                         "libgnome-desktop"))
        return env

    def _sanitize_pc_files(self):
        """修正安装出的 .pc：prefix 指向包目录，剥掉不存在的 -I。

        上游 pkg.generate 写入的是构建期 prefix，装进包后必须改写，否则下游
        的 PkgConfigDeps/CMakeDeps 会指向不存在路径（Imported target 报
        non-existent path）。
        """
        pkg_inc = os.path.join(self.package_folder, "include")
        for pc in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig",
                                         "*.pc")):
            text = open(pc, encoding="utf-8").read()
            lines = []
            for line in text.splitlines(keepends=True):
                if line.startswith("prefix="):
                    lines.append(f"prefix={self.package_folder}\n")
                    continue
                if line.startswith(("Cflags:", "Cflags.private:")):
                    head, sep, body = line.partition(":")
                    kept = []
                    for token in body.split():
                        match = token.startswith("-I")
                        if not match:
                            kept.append(token)
                            continue
                        path = token[2:].strip('"')
                        path = path.replace("${prefix}", self.package_folder)
                        path = path.replace("${includedir}", pkg_inc)
                        path = path.replace("${exec_prefix}", self.package_folder)
                        path = path.replace("${datadir}",
                                            os.path.join(self.package_folder, "share"))
                        path = path.replace("${libdir}",
                                            os.path.join(self.package_folder, "lib"))
                        if os.path.isdir(path):
                            kept.append(token)
                        else:
                            self.output.info(
                                f"{os.path.basename(pc)}: drop non-existent -I {token}")
                    lines.append(head + sep + " " + " ".join(kept) + "\n")
                    continue
                lines.append(line)
            open(pc, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _sign_build_artifacts(self):
        """给构建目录内的 .so 与 tests/ 下的测试程序补签名（OHOS 执行要求）。"""
        if self.settings.os != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip build signing")
            return
        candidates = []
        candidates.extend(glob.glob(os.path.join(self.build_folder, "**", "*.so*"),
                                    recursive=True))
        test_dir = os.path.join(self.build_folder, "tests")
        for program in ("bg-slide-show", "wall-clock", "wallclock-reftest",
                        "languages"):
            path = os.path.join(test_dir, program)
            if os.path.isfile(path):
                candidates.append(path)
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            self._sign_elf(binary)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        patterns = [os.path.join(self.package_folder, "lib", "**", "*.so*"),
                    os.path.join(self.package_folder, "bin", "**", "*")]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(shlex.join([signer, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))
