import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, copy, save, load
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class LibaccountsGlibConan(ConanFile):
    name = "libaccounts-glib"
    version = "1.27"
    description = "GLib-based library for managing online account information"
    license = "LGPL-2.1"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-glib"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")

    def build_requirements(self):
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        pc = PkgConfigDeps(self)
        pc.generate()

    def _augment_pkgconfig_files(self):
        """Add missing variables to conan-generated .pc files.

        Conan's PkgConfigDeps generates minimal .pc files. Some meson
        projects need extra variables (e.g., glib_genmarshal) that are
        only present in the upstream package's .pc files. We add them
        to the conan-generated files in the generators directory.
        """
        gen_dir = self.generators_folder
        glib = self.dependencies.get("glib")
        if not glib:
            return

        glib_pkg = glib.package_folder
        glib_bin = os.path.join(glib_pkg, "bin")

        # glib-2.0.pc needs glib_genmarshal, gobject_query, glib_mkenums
        glib_pc = os.path.join(gen_dir, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            content = load(self, glib_pc)
            additions = []
            for var, tool in [("glib_genmarshal", "glib-genmarshal"),
                              ("gobject_query", "gobject-query"),
                              ("glib_mkenums", "glib-mkenums")]:
                tool_path = os.path.join(glib_bin, tool)
                if os.path.isfile(tool_path) and var not in content:
                    additions.append(f"{var}={tool_path}")
            if additions:
                # Add after the existing variables
                content = content.rstrip("\n") + "\n" + "\n".join(additions) + "\n"
                save(self, glib_pc, content)

        # Also overlay the full set of glib .pc files (gio-2.0, gobject-2.0, etc.)
        # from the package, fixing prefix to the actual package dir.
        # Many packages ship .pc files with prefix=/ which breaks resolution.
        for dep_name in ["glib", "pcre2", "libffi"]:
            dep = self.dependencies.get(dep_name)
            if not dep:
                continue
            pkg_dir = dep.package_folder
            pc_dir = os.path.join(pkg_dir, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            for pc_file_path in glob.glob(os.path.join(pc_dir, "*.pc")):
                pc_name = os.path.basename(pc_file_path)
                gen_pc = os.path.join(gen_dir, pc_name)
                if not os.path.isfile(gen_pc):
                    # No conan-generated version, copy and fix prefix
                    lines = open(pc_file_path).readlines()
                    fixed = []
                    for line in lines:
                        stripped = line.strip()
                        if stripped == "prefix=/" or (
                            stripped.startswith("prefix=/")
                            and not stripped.startswith("prefix=/data")
                            and not stripped.startswith("prefix=/storage")
                        ):
                            # prefix is / or a broken relative path, fix it
                            fixed.append(f"prefix={pkg_dir}\n")
                        elif stripped.startswith("prefix=/storage") and pkg_dir not in stripped:
                            # Corrupted from cascading replacements
                            fixed.append(f"prefix={pkg_dir}\n")
                        else:
                            fixed.append(line)
                    with open(gen_pc, "w") as f:
                        f.writelines(fixed)

    def _patch_meson_native_file(self):
        """Add ar/ranlib/strip to the generated meson native file."""
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        content = open(native_file).read()
        if "[binaries]" in content and "ar =" not in content:
            content = content.replace(
                "[binaries]\n",
                "[binaries]\n"
                "ar = '/data/service/hnp/bin/llvm-ar'\n"
                "ranlib = '/data/service/hnp/bin/llvm-ranlib'\n"
                "strip = '/data/service/hnp/bin/llvm-strip'\n"
            )
            open(native_file, "w").write(content)

    def build(self):
        apply_conandata_patches(self)
        self._augment_pkgconfig_files()
        self._patch_meson_native_file()

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["accounts-glib"]
        self.cpp_info.includedirs = ["include", "include/libaccounts-glib"]
        self.cpp_info.set_property("pkg_config_name", "libaccounts-glib")
