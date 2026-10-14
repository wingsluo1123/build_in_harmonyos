#!/usr/bin/env python3
"""Conan recipe — atkmm 2.28.4 (Meson)

Official C++ bindings for ATK, the accessibility toolkit, on the **atkmm-1.6**
ABI line (the GTK3-era bindings line). Native build on HarmonyOS PC
(OHOS aarch64, clang 15, libc++). Meson drives the build; the official tarball
is a `meson dist` product that ships generated bindings under untracked/, so
mm-common / gmmproc / m4 are not required (maintainer-mode=false).

Real upstream dependencies (atkmm-2.28.4/meson.build L109-L119):
  - dependency('atk', version: '>= 2.12.0')
  - dependency('glibmm-2.4', version: '>= 2.46.2')  # glibmm 2.4 ABI line
pkg-config name: atkmm-1.6 (atkmm_api_version = '1.6').

ABI note: atkmm-1.6 != atkmm-2.36 (the glibmm-2.68 line adapted as
atkmm/2.36.4). gtkmm 3.24.x requires atkmm-1.6, hence this line exists
side by side with atkmm/2.36.4. Both conan packages can coexist
(different versions + different .pc names).

atkmm 2.28.4 ships no upstream tests (tarball has no tests/ directory and the
meson build registers no test()), so build() only configures+compiles;
consumer verification lives in test_package/.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class AtkmmConan(ConanFile):
    name = "atkmm"
    version = "2.28.4"
    description = "C++ bindings for ATK, the accessibility toolkit (atkmm-1.6)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/atkmm"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # atkmm 2.28.4 meson.build L109/L112/L119:
        #   glibmm-2.4 >= 2.46.2 (2.4 ABI line, sigc++-2.0 based),
        #   atk >= 2.12.0.
        # glibmm/2.66.9 is the 2.4-ABI recipe line (provides glibmm-2.4.pc /
        # giomm-2.4.pc) and atk/2.38.0.1.1 is the same atk that gtk/3.24.43
        # pulls, so the GTK3 graph stays single-versioned.
        self.requires("glibmm/2.66.9", transitive_headers=True, transitive_libs=True)
        self.requires("atk/2.38.0.1.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def _inject_meson_binaries(self):
        """Write ar/ranlib + pkg-config full paths into the meson native file.

        MesonToolchain only maps the c/cpp entries of tools.build:compiler_executables,
        so meson probes ar/ranlib by bare name (llvm-ar) and pkg-config by PATH. The
        clang toolchain lives in /data/service/hnp/bin (not on PATH during conan
        create on some workers), and meson cannot see the PkgConfigDeps .pc files
        without a usable pkg-config.
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
            pkg_config = shutil_which_pkg_config()
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
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        # 【skill: --pc-var 生成】atkmm 2.28.4 上游 meson.build L122 无条件执行
        #   gmmproc_dir = glibmm_dep.get_variable(pkgconfig: 'gmmprocdir')
        # glibmm/2.66.9 的 glibmm-2.4.pc 未定义该变量（gmmproc 仅在 maintainer
        # mode 下使用），因此把它补进生成的 glibmm-2.4.pc，否则 meson setup
        # 直接报 "Variable 'gmmprocdir' not found in the pkg-config file"。
        _pc = os.path.join(self.generators_folder, "glibmm-2.4.pc")
        if os.path.isfile(_pc) and "gmmprocdir" not in open(_pc).read():
            with open(_pc, "a") as _f:
                _f.write("gmmprocdir=${libdir}/glibmm-2.4/proc\n")
        tc = MesonToolchain(self)
        # 产物为动态库：libatkmm-1.6 不是系统同名库（不在 /lib、/lib64），
        # 由 Conan 管理依赖链（与 glibmm/pangomm-2.46 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，
        # 不需要 mm-common/gmmproc/m4。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失；上游默认
        # build-documentation=if-maintainer-mode，显式关闭以求确定性。
        tc.project_options["build-documentation"] = "false"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        # 上游 codegen/extradefs/meson.build L7 用
        #   cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')
        # 查找该库；它不在编译器的系统默认搜索路径，需要把 glibmm 的 libdir
        # 加入链接器搜索路径（经 conf 使 MesonToolchain 写进 native 文件的
        # cpp_link_args / c_link_args）。（pangomm-2.46.5 / atkmm-2.36.4 同款技法）
        dep_glibmm = self.dependencies.get("glibmm")
        if dep_glibmm:
            for _ld in dep_glibmm.cpp_info.libdirs:
                self.conf.define("tools.build:sharedlinkflags",
                                 self.conf.get("tools.build:sharedlinkflags", default=[]) + ["-L" + _ld])
                self.conf.define("tools.build:exelinkflags",
                                 self.conf.get("tools.build:exelinkflags", default=[]) + ["-L" + _ld])
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # atkmm 2.28.4 的 meson 未注册 test()（tarball 无 tests/ 目录），
        # 故无上游 meson 测试可执行；build() 只做 configure+compile。

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def package_info(self):
        # 头文件布局：include/atkmm-1.6 + lib/atkmm-1.6/include（atkmmconfig.h）
        # + include（atkmm.h 伞头，与 atkmm/2.36.4 同款）。
        self.cpp_info.includedirs = [
            "include",
            "include/atkmm-1.6",
            "lib/atkmm-1.6/include",
        ]
        self.cpp_info.libs = ["atkmm-1.6"]
        self.cpp_info.set_property("pkg_config_name", "atkmm-1.6")

    def _sign_shared_libs(self):
        # 原生 OHOS worker：meson install 改写了 rpath，.so 需要重新 codesign
        # 才能 dlopen/执行（E135）。交叉 Docker SDK 无 binary-sign-tool → 跳过。
        if self.settings.os != "OHOS":
            return
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            self.output.warning("binary-sign-tool 不存在，跳过 .so 签名")
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        for so in sos:
            tmp_signed = so + ".signed"
            # 正确签名语法：sign -selfSign 1 -inFile X -outFile Y
            # （对 .so 先移除 .codesign 段再签名，与 abbtr/acme-client 既有做法一致）。
            if os.path.isfile(objcopy):
                self.run('"{}" --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, so))
            self.run('"{}" sign -selfSign 1 -inFile "{}" -outFile "{}"'.format(sign_tool, so, tmp_signed))
            if os.path.isfile(tmp_signed):
                os.replace(tmp_signed, so)


def shutil_which_pkg_config():
    import shutil
    return shutil.which("pkg-config") or shutil.which("pkgconf")
