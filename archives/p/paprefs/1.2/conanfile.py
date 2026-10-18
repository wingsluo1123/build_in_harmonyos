#!/usr/bin/env python3
"""Conan recipe — paprefs 1.2 (PulseAudio Preferences, GTK GUI application).

Meson project, single C++ source (src/paprefs.cc).  Upstream meson.build
resolves everything via pkg-config:
    gtkmm-3.0 / giomm-2.4 (glibmm ABI 2.4 line) / sigc++-2.0 / libpulse
So the recipe pins the meson toolchain via MesonToolchain, injects pkg-config
+ ar/ranlib into the meson native file, and writes flat .pc files
(gtkmm-3.0 / giomm-2.4 / sigc++-2.0 / libpulse) resolved from the dependency
graph — see _write_flat_pcs() for why PkgConfigDeps is not usable here.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class PaprefsConan(ConanFile):
    name = "paprefs"
    version = "1.2"
    description = "PulseAudio Preferences — GTK dialog for PulseAudio server/network configuration"
    license = "GPL-2.0-or-later"
    homepage = "https://freedesktop.org/software/pulseaudio/paprefs/"
    url = "https://gitlab.freedesktop.org/pulseaudio/paprefs"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # intl-wrapper.c 由配方自带（新文件无法以补丁形式入库）：source()
        # 拷入源码树 src/，由 patches/0001 的 meson.build 改动编进 paprefs
        # 可执行文件（g_libintl_* → libintl_* 转发，E508）。
        copy(self, "intl-wrapper.c",
             src=os.path.join(self.recipe_folder, "res"),
             dst=os.path.join(self.export_sources_folder, "src"))

    def validate(self):
        # R32
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # gtkmm-3.0 ( gtkmm/gdkmm C++ bindings + whole glibmm/gtk/atkmm/
        # cairomm/pangomm/gdk-pixbuf graph with pkg-config components).
        self.requires("gtkmm/3.24.11", transitive_headers=True, transitive_libs=True)
        # gtkmm/3.24.11 pins libsigc/2.10.8 with override=True; paprefs'
        # meson dependency('sigc++-2.0') resolves through the same graph.
        # Keep the pin aligned to avoid a version conflict between
        # glibmm/2.66.9 (libsigc/2.10.x) and cairomm/pangomm (libsigc/2.12.x):
        # sigc++-2.0 ABI is stable across 2.x (SONAME libsigc-2.0.so.0).
        self.requires("libsigc/2.10.8", override=True)
        # expat 冲突消解：pulseaudio/17.0 钉 expat/2.8.2，而 gtk 图内已有
        # 依赖钉 SONAME 修复版 expat/2.8.2.1（2.8.2 的 .so 无 SONAME，
        # 跨包加载失败，见 cairo/1.18.4 配方注释与 fceux 归档先例）。
        # 统一 override 到 2.8.2.1。
        self.requires("expat/2.8.2.1", override=True)
        # libpulse (client library component "pulse" of pulseaudio/17.0)
        self.requires("pulseaudio/17.0", transitive_headers=True, transitive_libs=True)
        # gettext（知识库 ohos-nls-libintl + E508）：glib 自带的 proxy
        # libintl.h 把 gettext 家族宏改名为 g_libintl_*，OHOS 上无人提供
        # 这些符号 → 链接 undefined。加 gettext 包（libintl.a）+ 源内
        # intl-wrapper.c（见 patches）做 g_libintl_* → libintl_* 转发。
        self.requires("gettext/0.22.5.1")

    def build_requirements(self):
        # 上游唯一的测试用例在 doc/meson.build：
        #   if tidy.found() -> test('XHTML documentation uses correct mark-up',
        #                           tidy, args: ['-e', readme_html])
        # 没有 tidy 时 meson 根本不注册该 test（不是 SKIP），上游用例就会
        # 变成「0/1 未执行」。制品仓已有 tidy-html5/5.8.0（cgit-pink 等配方
        # 已在用同一工具依赖），作为 build 侧工具依赖引入，使上游测试真实可执行。
        self.tool_requires("tidy-html5/5.8.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conan 2 cache 构建时 export_sources 已在 source_folder 内（src ==
        # dst 时 copy() 抛异常），仅缺失时补拷（astroterm res/ 同款）。
        dst = os.path.join(self.source_folder, "src", "intl-wrapper.c")
        if not os.path.isfile(dst):
            candidates = [
                os.path.join(self.export_sources_folder or "", "src", "intl-wrapper.c"),
                os.path.join(self.recipe_folder, "res", "intl-wrapper.c"),
            ]
            for src in candidates:
                if src and os.path.isfile(src) and \
                        os.path.abspath(src) != os.path.abspath(dst):
                    copy(self, "intl-wrapper.c", src=os.path.dirname(src),
                         dst=os.path.join(self.source_folder, "src"))
                    break

    def _inject_meson_binaries(self):
        """Pin ar/ranlib + pkg-config into the meson native/cross file.

        MesonToolchain only maps c/cpp of tools.build:compiler_executables;
        meson probes ar/ranlib/pkg-config by bare name via PATH.  The clang
        toolchain lives in /data/service/hnp/bin (not on PATH during conan
        create on some workers), and without a usable pkg-config meson cannot
        see the PkgConfigDeps .pc files (same as gtkmm/3.24.11).
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            compiler = ce.get("cpp") or ce.get("c") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def _collect_cpp_flags(self, cpp_info, pkg_root, incs, libdirs, libs):
        """Accumulate absolute include/lib dirs and lib names from one
        cpp_info node (top-level or a component)."""
        for d in (cpp_info.includedirs or []):
            full = d if os.path.isabs(d) else os.path.join(pkg_root, d)
            if full not in incs:
                incs.append(full)
        for d in (cpp_info.libdirs or []):
            full = d if os.path.isabs(d) else os.path.join(pkg_root, d)
            if full not in libdirs:
                libdirs.append(full)
        for lib in (cpp_info.libs or []):
            if lib not in libs:
                libs.append(lib)

    def _write_flat_pcs(self):
        """Write flat .pc files for the four upstream dependency() names.

        conan's PkgConfigDeps cannot be used here: atkmm/2.28.4's recipe
        (rev 2026-10-14) exposes a flat cpp_info while gtkmm/3.24.11's
        package_info still references component "atkmm::atkmm-1.6", so
        PkgConfigDeps dies with
        "Component 'atkmm::atkmm-1.6' not found in 'atkmm' package
        requirement" before writing a single .pc.  Fixing that means editing
        another package's recipe (forbidden by W2 atomicity), so the recipe
        side instead flattens the whole host dependency graph into one
        aggregate -I/-L/-l set and emits the exact .pc names paprefs'
        meson.build asks for.  paprefs is an application, so linking the
        aggregate is harmless.
        """
        incs, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            cpp_info = getattr(dep, "cpp_info", None)
            pkg_root = getattr(dep, "package_folder", None)
            if not cpp_info or not pkg_root:
                continue
            self._collect_cpp_flags(cpp_info, pkg_root, incs, libdirs, libs)
            for comp in (cpp_info.components or {}).values():
                self._collect_cpp_flags(comp, pkg_root, incs, libdirs, libs)

        def lib_exists(lib):
            # 只链接实际存在的库：gettext 配方声明 asprintf 但包内无
            # libasprintf（cpp_info 与包内容不一致），-lasprintf 直接炸链接。
            for d in libdirs:
                if (os.path.isfile(os.path.join(d, "lib%s.so" % lib)) or
                        os.path.isfile(os.path.join(d, "lib%s.a" % lib))):
                    return True
            return False

        libs = [lib for lib in libs if lib_exists(lib)]
        # gettext 特判：① 丢弃 paprefs 用不到的 gettextpo/textstyle
        # （libgettextpo.so 自身引用未解析的 libintl_*，被拉进链接只会炸）；
        # ② -lintl 不能用——glib 包带了个自身 U 状态的 libintl.so 会抢先
        # 解析，直接用 gettext 包内的 libintl.a 全路径（含
        # gl_get_setlocale_null_lock 等 gnulib 符号）。
        libs = [lib for lib in libs
                if lib not in ("gettextpo", "textstyle", "asprintf", "intl")]
        gettext_dep = self.dependencies.get("gettext")
        extra_link = ""
        if gettext_dep is not None and getattr(gettext_dep, "package_folder", None):
            intl_a = os.path.join(gettext_dep.package_folder, "lib", "libintl.a")
            if os.path.isfile(intl_a):
                extra_link = " " + intl_a
        cflags = " ".join("-I%s" % d for d in incs)
        libs_args = " ".join(["-L%s" % d for d in libdirs] +
                             ["-l%s" % lib for lib in libs]) + extra_link

        def dep_version(name):
            dep = self.dependencies.get(name)
            ref = getattr(dep, "ref", None) if dep is not None else None
            return str(ref.version) if ref is not None else "1.0"

        # Version 必须是真实版本：上游 meson 有 version 约束
        # （giomm-2.4 >= 2.26），写死占位版本会触发 "Invalid version"。
        deps = [
            ("gtkmm-3.0", dep_version("gtkmm"),
             "GTK+3 C++ bindings (flattened conan graph)"),
            ("giomm-2.4", dep_version("glibmm"),
             "gio C++ bindings (flattened conan graph)"),
            ("sigc++-2.0", dep_version("libsigc"),
             "sigc++ 2.x C++ bindings (flattened conan graph)"),
            ("libpulse", dep_version("pulseaudio"),
             "PulseAudio client library (flattened conan graph)"),
        ]
        for name, version, desc in deps:
            pc = os.path.join(self.generators_folder, "%s.pc" % name)
            with open(pc, "w", encoding="utf-8") as f:
                f.write(
                    "Name: %s\n"
                    "Description: %s\n"
                    "Version: %s\n"
                    "Cflags: %s\n"
                    "Libs: %s\n" % (name, desc, version, cflags, libs_args))

    def _build_env(self):
        # tool_requires（tidy-html5，可执行文件名为 tidy）的 bin 必须进 PATH：
        # meson setup 用 find_program('tidy') 决定是否注册上游文档测试
        # （'XHTML documentation uses correct mark-up'），测试运行时也要能解析到它。
        # 两处 Conan 2 语义必须踩准：
        #   1) self.run(env=...) 的 env 是"环境脚本文件名列表"，不是
        #      "VAR=VALUE" 字符串——传字符串列表会被静默忽略，变量根本不生效；
        #      正确姿势是 Environment 定义变量 + vars(self).apply()。
        #   2) dependencies.get() 在依赖缺失时直接 raise KeyError（无
        #      check=False 退路），故先用 in 判断，工具缺失时退化为系统 PATH。
        env = Environment()
        path = os.environ.get("PATH", "")
        tidy = (self.dependencies.build.get("tidy-html5")
                if "tidy-html5" in self.dependencies.build else None)
        if tidy and tidy.package_folder:
            path = os.path.join(tidy.package_folder, "bin") + os.pathsep + path
        env.define("PATH", path)
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        return env

    def _meson_file_arg(self):
        for nf_name in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if os.path.isfile(nf):
                return "--%s-file %s" % ("cross" if "cross" in nf_name else "native", nf)
        return ""

    def generate(self):
        tc = MesonToolchain(self)
        # Application build; paprefs has no library targets.
        tc.project_options["default_library"] = "static"
        # lynx/tidy are only for HTML/README doc generation (lynx default
        # false upstream; tidy is required:false already).
        tc.project_options["lynx"] = "false"
        # Never let meson fetch subprojects over the network (CI has none).
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()
        self._write_flat_pcs()

    def build(self):
        apply_conandata_patches(self)
        file_arg = self._meson_file_arg()
        env = self._build_env()
        with env.vars(self).apply():
            self.run(
                'meson setup "{src}" "{bld}" --prefix="{prefix}" {file_arg}'.format(
                    src=self.source_folder, bld=self.build_folder,
                    prefix=self.package_folder, file_arg=file_arg))
            ninja = os.environ.get("HMBS_NINJA") or "ninja"
            self.run('"{ninja}" -C "{bld}" -j1'.format(
                ninja=ninja, bld=self.build_folder))
            # 上游测试套件：doc/meson.build 在 tidy 可用时注册 1 个用例
            # （'XHTML documentation uses correct mark-up'，tidy -e README.html）。
            # tidy 由 build_requirements 提供，故这里 1/1 真实执行（非 SKIP）。
            self.run('meson test -C "{bld}" --print-errorlogs'.format(
                bld=self.build_folder))

    def package(self):
        env = self._build_env()
        with env.vars(self).apply():
            self.run('meson install -C "{bld}" --no-rebuild'.format(
                bld=self.build_folder))
        self._sign_package_binaries()

    def _sign_package_binaries(self):
        # E135：OHOS worker 上 meson/clang 产物需要 codesign 才能 dlopen/执行
        # （gtkmm/atkmm 等配方同款）。交叉/SDK 环境无 binary-sign-tool 则跳过。
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            cand = os.path.join(os.path.dirname(cc), "llvm-objcopy")
            if os.path.isfile(cand):
                objcopy = cand
        import glob
        targets = []
        for sub in ("bin", "lib"):
            targets += glob.glob(os.path.join(self.package_folder, sub, "**", "*"),
                                 recursive=True)
        for f in targets:
            if not (os.path.isfile(f) and (f.endswith(".so") or ".so." in f or
                                           os.access(f, os.X_OK))):
                continue
            if objcopy and os.path.isfile(objcopy):
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
