#!/usr/bin/env python3
"""Conan recipe for xmedcon 0.26.1-gtk3.

Upstream is a legacy Autotools project (XMedCon medical image converter):
`libmdc` (LGPL-2.1+) plus the `medcon` CLI and the GTK+3 `xmedcon` GUI
(GPL-2.0+).  The bundled formats (dicom/ljpg/nifti/tpc) build from libs/,
zlib is required for PNG+NIFTI, libpng for PNG output, and the GUI probes
`gtk+-3.0` / `gdk-pixbuf-2.0` via pkg-config -- all available in the repo.

The source URL and SHA256 are kept in this recipe (no conandata.yml) so the
package never enters the CI pre-download branch (see xmodem knowledge).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import copy, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XmedconConan(ConanFile):
    name = "xmedcon"
    version = "0.26.1-gtk3"
    description = "Medical image conversion utility (DICOM, ECAT, Analyze, NIfTI, InterFile) with GTK+3 GUI"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "https://xmedcon.sourceforge.io"
    url = "https://sourceforge.net/projects/xmedcon"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _source_url = "https://master.dl.sourceforge.net/project/xmedcon/XMedCon-Source/0.26.1/xmedcon-0.26.1-gtk3.tar.gz?viasf=1"
    _source_sha256 = "4bc81e014b56873fe9a8e942f97fd0565dc891cf216f817de92647bf0285f40f"

    def build_requirements(self):
        self.tool_requires("autotools-dev/20240727.1-nmu1")
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            filename="xmedcon-0.26.1-gtk3.tar.gz",
            strip_root=True,
        )

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # PNG/NIFTI/TPC use bundled libs from libs/; keep formats default-on.
            "--with-pic",
            "--disable-static",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        self._stage_autotools_aux_files()
        self._make_configure_executable()
        self._patch_configure_tmpdir()
        self._write_ohos_mktemp_wrapper()

        with self._build_environment().vars(self).apply():
            autotools = Autotools(self)
            if str(self.settings.os) == "OHOS":
                self._configure_for_ohos(autotools)
                # umask 000: HMDFS 拒绝写入 mktemp -d 的 0700 目录;统一放开权限。
                self.run(
                    f"umask 000 && {self._source_conanbuild()}make -j1",
                    cwd=self.source_folder,
                )
            else:
                autotools.configure()
                autotools.make(args=["-j1"])

    def package(self):
        with self._build_environment().vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self.run(
                    f"umask 000 && {self._source_conanbuild()}make install "
                    f"DESTDIR={shlex.quote(self.package_folder)}",
                    cwd=self.source_folder,
                )
            else:
                Autotools(self).install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", src=os.path.join(self.source_folder, "libs"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["mdc"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # helpers shared with the xsane/gtk2 OHOS autotools recipes
    # ------------------------------------------------------------------
    def _stage_autotools_aux_files(self):
        misc = os.path.join(self.dependencies.build["autotools-dev"].package_folder, "share", "misc")
        for name in ("config.guess", "config.sub"):
            copy(self, name, src=misc, dst=self.source_folder)

    def _make_configure_executable(self):
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)

    def _patch_configure_tmpdir(self):
        # 与 gtk2/xsane 配方同款修复:HMDFS 对 mktemp -d(umask 077 -> 0700)
        # 目录拒绝写入且静默忽略 chmod;autoconf 2.71 把临时目录硬编码在 cwd。
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8", errors="replace") as h:
            content = h.read()
        replaced = [
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp=`(umask 000 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` && { chmod 777 "$tmp" 2>/dev/null || true; } &&'),
            ("tmp=./conf$$-$RANDOM",
             "tmp=${TMPDIR:-.}/conf$$-$RANDOM"),
        ]
        optional = [
            ("(umask 077 && mkdir \"$tmp\")",
             "(umask 000 && mkdir \"$tmp\")"),
        ]
        changed = False
        for old, new in replaced:
            if new in content:
                continue
            if old not in content:
                raise ConanException(f"configure tmpdir pattern not found: {old[:50]}")
            content = content.replace(old, new, 1)
            changed = True
        for old, new in optional:
            if old in content and new not in content:
                content = content.replace(old, new, 1)
                changed = True
        if changed:
            with open(configure, "w", encoding="utf-8", newline="\n") as h:
                h.write(content)
            self.output.info("patched configure tmpdir to ${TMPDIR:-.} umask-000")

    def _build_environment(self):
        env = Environment()
        pkgconf_bin = os.path.join(self.dependencies.build["pkgconf"].package_folder, "bin")
        if str(self.settings.os) == "OHOS":
            env.prepend_path("PATH", self._ohos_wrapper_dir())
            # 工具链目录必须显式入 PATH：CI worker 的 PATH 不含 hnp/bin，
            # configure 开头的 dirname/expr/sed 探测会命中 toybox 版本并失败，
            # 进而 srcdir 推导为空 → "cannot find sources"。（真机靠 runner 手动加）
            env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("PATH", pkgconf_bin)
        env.prepend_path("PATH", os.path.join(self.dependencies["gtk"].package_folder, "bin"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.define("PKG_CONFIG", os.path.join(pkgconf_bin, "pkgconf"))
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
        if str(self.settings.os) == "OHOS":
            # autoconf 2.72+ AC_PROG_CC_FOR_BUILD 探测构建端 cc;设备上的
            # ~/usr/local/bin/cc 未签名不可执行, 显式指向同一 clang。
            env.define("CC_FOR_BUILD", compiler_executables.get("c", "clang"))
            env.define("CXX_FOR_BUILD", compiler_executables.get("cpp", "clang++"))
        self._define_ohos_binary_tools(env, compiler_executables)
        tmpdir = os.path.join(self.source_folder, ".tmp")
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

    def _source_conanbuild(self):
        # 手工驱动 configure/make 时必须 source 生成的 conanbuild.sh,
        # 否则 AutotoolsDeps 注入的 -L/-I 与编译器 flags 全部丢失
        # (表现为 configure 链接测试 "C compiler cannot create executables")。
        # 但要 unset LIBS: autoconf 2.72+ 的 AC_PROG_CC_FOR_BUILD 用默认 CFLAGS
        # 链接构建端可执行文件时继承 LIBS, 目标库(-lgtk-3...)必然找不到。
        conanbuild = os.path.join(self.build_folder, "conanbuild.sh")
        if os.path.isfile(conanbuild):
            return f'. "{conanbuild}" && unset LIBS && '
        return ""

    def _configure_for_ohos(self, autotools):
        shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        # LIBS= 作为 VAR=VALUE 参数显式清空: autoconf 2.72+ 的
        # AC_PROG_CC_FOR_BUILD "compiler works" 测试继承初始 LIBS,
        # 用默认 CFLAGS 链接 -lgtk-3... 必挂 (unset 在部分设备 shell 下
        # 不可靠, 命令行参数由 autoconf 直接写入 ac_cv_env)。
        # srcdir=. 显式固化为 in-source: 绕开 configure 开头用 dirname/expr
        # 推导 srcdir 的脆弱路径（PATH 缺 GNU 工具或 fork 受限时推导为空 →
        # "cannot find sources ... in or .."）。cwd=self.source_folder 恒为
        # 源码根，source/medcon.c 就在其下。
        configure_args = (autotools._configure_args or "") + " LIBS="
        self.run(
            f"umask 000 && {self._source_conanbuild()}"
            f"srcdir=. {shlex.quote(shell)} {shlex.quote(configure)} {configure_args}",
            cwd=self.source_folder,
        )
