#!/usr/bin/env python3
"""Conan recipe — graphene 1.10.8 (Meson).

Graphene is a thin layer of graphic data types for 2D/3D graphics
(vectors, matrices, quaternions, etc.) used by GTK4 and GNOME.
It builds libgraphene-1.0.so and provides the graphene-1.0 pkg-config.

On OHOS aarch64: SSE2 and GCC vector intrinsics are disabled,
ARM NEON is enabled for SIMD optimisation.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.env import Environment


class GrapheneConan(ConanFile):
    name = "graphene"
    version = "1.10.8"
    description = "A thin layer of graphic data types for 2D/3D graphics"
    license = "MIT"
    homepage = "https://github.com/ebassi/graphene"
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
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        # MesonToolchain omits ar/ranlib; cross builds also omit pkg-config,
        # so Meson reports "Found pkg-config: NO" and cannot see
        # PkgConfigDeps .pc files. Inject full paths into native file.
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
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
            if (
                pkg_config
                and "\npkg-config =" not in content
                and "\npkgconfig =" not in content
            ):
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1
            )
            with open(nf, "w") as f:
                f.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["libdir"] = "lib"
        tc.project_options["gobject_types"] = "true"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["sse2"] = "false"
        tc.project_options["gcc_vector"] = "false"
        tc.project_options["arm_neon"] = "true"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()
        self._setup_lld_env()

    def _setup_lld_env(self):
        """Set LD_LIBRARY_PATH for OHOS SDK lld linker (needs libxml2.so.16)."""
        ce = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict) or {}
        cc = ce.get('c') or ''
        if not cc:
            return
        real_cc = os.path.realpath(cc)
        bindir = os.path.dirname(real_cc)
        for libdir in [os.path.join(bindir, 'lib'),
                       os.path.join(bindir, '..', 'lib')]:
            abspath = os.path.abspath(libdir)
            if os.path.isfile(os.path.join(abspath, 'libxml2.so.16')):
                env = Environment()
                env.prepend_path('LD_LIBRARY_PATH', abspath)
                env.vars(self, scope='build').save_script('conanbuildenv_lld')
                break

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        Meson(self).install()
        # R32: sign shared libs on OHOS
        if self.settings.os in ("Linux", "OHOS") and self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(
                0, os.path.join(os.path.dirname(cc), "llvm-objcopy")
            )
        objcopy = next(
            (p for p in candidates_objcopy if p and os.path.isfile(p)), None
        )
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skip OHOS codesign (cross/SDK env)"
            )
            return
        for so in sos:
            if objcopy:
                self.run(
                    '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                        oc=objcopy, f=so
                    )
                )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=so
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["graphene-1.0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/graphene-1.0", "lib/graphene-1.0/include"]
        self.cpp_info.set_property("cmake_file_name", "graphene-1.0")
        self.cpp_info.set_property(
            "cmake_target_name", "graphene-1.0::graphene-1.0"
        )
        self.cpp_info.set_property("pkg_config_name", "graphene-1.0")
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
