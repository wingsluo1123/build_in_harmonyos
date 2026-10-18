#!/usr/bin/env python3
"""Conan recipe for xarchive 0.2.8-6.

Upstream is a legacy (2005) GTK+2 GUI front-end for command-line archive
tools (tar/zip/rar/...), hosted on SourceForge.  The recipe follows the
xsane/0.999 pattern for legacy Autotools GTK2 applications:

  - gtk+-2.0 pkg-config probe resolves against the repo's native
    gtk2/2.24.33 package (pkg_config_name "gtk+-2.0");
  - 2005-era config.guess/config.sub are replaced with autotools-dev
    copies (E-series: ancient scripts do not know aarch64-ohos);
  - HMDFS-safe configure tmpdir patch + mktemp wrapper (E114 pattern,
    same as gtk2/xsane recipes);
  - OHOS: /system/bin/sh as CONFIG_SHELL, umask 000, DESTDIR install,
    llvm binary tools;
  - the GUI itself is never launched headless; the consumer smoke test
    runs `xarchive --help` which exits inside g_option_context_parse()
    *before* gtk_init(), so it succeeds without an X server and still
    exercises the full dynamic-linking chain (libc/gtk-x11/gdk/...).
"""
import io
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XarchiveConan(ConanFile):
    name = "xarchive"
    version = "0.2.8-6"
    description = "XArchive — GTK+2 graphical front-end for command-line archivers (tar, zip, rar, 7z, deb, ...)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/xarchive/"
    url = "https://sourceforge.net/projects/xarchive/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("autotools-dev/20240727.1-nmu1")
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        self.requires("gtk2/2.24.33")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        # 交叉编译下 AC_REPLACE_FNMATCH 的运行时探测被判 no → 触发
        # AC_CONFIG_LINKS(fnmatch.h:fnmatch_.h), 而上游 tarball 并未携带
        # fnmatch_.h → config.status 报 "file not found"。musl fnmatch 工作正常,
        # 用 autoconf cache 变量直接跳过探测。
        tc.configure_args.append("ac_cv_func_fnmatch_works=yes")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._stage_autotools_aux_files()
        self._make_configure_executable()
        self._patch_configure_tmpdir()
        self._write_ohos_mktemp_wrapper()

        with self._build_environment().vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            if str(self.settings.os) == "OHOS":
                # HMDFS: make 生成的 wrapper 脚本/桌面文件需组/其他可读,
                # umask 000 与 gtk2/xsane 配方同口径
                self.run("umask 000 && make -j1", cwd=self.build_folder)
            else:
                autotools.make(args=["-j1"])

    def package(self):
        with self._build_environment().vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self.run(
                    f"umask 000 && make install DESTDIR={shlex.quote(self.package_folder)}",
                    cwd=self.build_folder,
                )
            else:
                Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # helpers (xsane/0.999 同款)
    # ------------------------------------------------------------------

    def _stage_autotools_aux_files(self):
        misc = os.path.join(self.dependencies.build["autotools-dev"].package_folder, "share", "misc")
        copy(self, "config.guess", src=misc, dst=self.source_folder)
        copy(self, "config.sub", src=misc, dst=self.source_folder)
        # 上游将 aux 脚本放在 config/ 子目录
        copy(self, "config.guess", src=misc, dst=os.path.join(self.source_folder, "config"))
        copy(self, "config.sub", src=misc, dst=os.path.join(self.source_folder, "config"))

    def _make_configure_executable(self):
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)

    def _patch_configure_tmpdir(self):
        # HMDFS 对 mktemp -d(0700) 目录拒绝写入且静默忽略 chmod(与 gtk2/xsane
        # 配方同款); autoconf 2.59 把临时目录硬编码在 cwd。改写 configure 使其
        # 落在 ${TMPDIR:-.} 且 umask 000。使用 replace_in_file, 也便于
        # clean-verify G0 将本配方识别为"运行时修复型"。
        configure = os.path.join(self.source_folder, "configure")
        patterns = [
            'tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&',
            'tmp=`(umask 000 && mktemp -d "${TMPDIR:-.}/confstatXXXXXX") 2>/dev/null` && { chmod 777 "$tmp" 2>/dev/null || true; } &&',
            'tmp=./confstat$$-$RANDOM',
            'tmp=${TMPDIR:-.}/confstat$$-$RANDOM',
            '(umask 077 && mkdir $tmp)',
            '(umask 000 && mkdir $tmp)',
        ]
        with io.open(configure, "r", encoding="utf-8", errors="replace") as h:
            content = h.read()
        changed = False
        for i in range(0, len(patterns), 2):
            old, new = patterns[i], patterns[i + 1]
            if new in content or old not in content:
                continue
            replace_in_file(self, configure, old, new)
            with io.open(configure, "r", encoding="utf-8", errors="replace") as h:
                content = h.read()
            changed = True
        if changed:
            self.output.info("patched configure tmpdir to ${TMPDIR:-.} umask-000")
        else:
            self.output.info("configure tmpdir: no known pattern found, skip")

    def _build_environment(self):
        env = Environment()
        pkgconf_bin = os.path.join(self.dependencies.build["pkgconf"].package_folder, "bin")
        gtk2_pkg = self.dependencies["gtk2"].package_folder
        if str(self.settings.os) == "OHOS":
            env.prepend_path("PATH", self._ohos_wrapper_dir())
        env.prepend_path("PATH", pkgconf_bin)
        env.prepend_path("PATH", os.path.join(gtk2_pkg, "bin"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.define("PKG_CONFIG", os.path.join(pkgconf_bin, "pkgconf"))
        # 2005 年 src/Makefile 无 VPATH include 路径: widgets_gtk.h 以
        # #include"icons/xarchive.xpm" 源码根为基准, VPATH 编译找不到 →
        # 补 -I<top_srcdir>; 老 configure 把 CPPFLAGS 捕获进 CONFIGURE_CFLAGS
        env.append("CPPFLAGS", f"-I{self.source_folder}")
        if str(self.settings.os) == "OHOS":
            env.define("CONFIG_SHELL", "/system/bin/sh")
            env.define("SHELL", "/system/bin/sh")
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler_executables = dict(compiler_executables or {})
        if str(self.settings.os) == "OHOS":
            compiler_executables.setdefault("c", "/data/service/hnp/bin/clang")
            compiler_executables.setdefault("cpp", "/data/service/hnp/bin/clang++")
        if compiler_executables.get("c"):
            env.define("CC", compiler_executables["c"])
        if compiler_executables.get("cpp"):
            env.define("CXX", compiler_executables["cpp"])
        self._define_ohos_binary_tools(env, compiler_executables)
        tmpdir = os.path.join(self.build_folder, ".conan-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        return env

    def _ohos_wrapper_dir(self):
        return os.path.join(self.source_folder, ".conan-ohos-bin")

    def _write_ohos_mktemp_wrapper(self):
        if str(self.settings.os) != "OHOS":
            return

        wrapper_dir = self._ohos_wrapper_dir()
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        save(
            self,
            wrapper,
            "\n".join([
                "#!/system/bin/sh",
                'out=$(/system/bin/mktemp "$@" 2>/dev/null || /data/service/hnp/bin/mktemp "$@") || exit 1',
                "# HMDFS denies writes into mktemp dirs whose group/other bits are",
                "# all zero (mktemp -d -> 0700) and silently ignores chmod there;",
                "# recreate via mkdir at the same path so the mode bits are",
                "# inherited (umask 000 builds -> writable).",
                'if [ -d "$out" ]; then rmdir "$out" 2>/dev/null && mkdir "$out" 2>/dev/null; fi',
                'chmod 0755 "$out" 2>/dev/null || true',
                'echo "$out"',
                "",
            ]),
        )
        os.chmod(wrapper, 0o755)

    def _define_ohos_binary_tools(self, env, compiler_executables):
        if str(self.settings.os) != "OHOS":
            return

        compiler = compiler_executables.get("c")
        tool_dir = os.path.dirname(compiler) if compiler else "/data/service/hnp/bin"
        for env_name, tool_name in {
            "AR": "llvm-ar",
            "NM": "llvm-nm",
            "RANLIB": "llvm-ranlib",
            "STRIP": "llvm-strip",
        }.items():
            candidate = os.path.join(tool_dir, tool_name)
            if os.path.isfile(candidate):
                env.define(env_name, candidate)
