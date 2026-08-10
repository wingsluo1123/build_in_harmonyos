import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, copy, save, load
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class LibaccountsQtConan(ConanFile):
    name = "libaccounts-qt"
    version = "1.13"
    description = "Qt library for managing online account configurations and authentication"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/accounts-squad/libaccounts-qt"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        self.requires("glib/2.84.0")
        self.requires("libaccounts-glib/1.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pc = PkgConfigDeps(self)
        pc.generate()

    def _fix_and_overlay_pkgconfig(self):
        """Fix pkg-config .pc files and overlay package's own .pc files."""
        gen_dir = self.generators_folder

        for dep_name in ["glib", "pcre2", "libffi", "libaccounts-glib"]:
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
                lines = open(pc_file_path).readlines()
                fixed = []
                for line in lines:
                    stripped = line.strip()
                    if stripped == "prefix=/" or (
                        stripped.startswith("prefix=/")
                        and not stripped.startswith("prefix=/data")
                        and not stripped.startswith("prefix=/storage")
                    ):
                        fixed.append(f"prefix={pkg_dir}\n")
                    elif stripped.startswith("prefix=/storage") and pkg_dir not in stripped:
                        fixed.append(f"prefix={pkg_dir}\n")
                    else:
                        fixed.append(line)
                with open(gen_pc, "w") as f:
                    f.writelines(fixed)

        # Augment conan-generated glib-2.0.pc with glib_genmarshal etc.
        glib = self.dependencies.get("glib")
        if glib:
            glib_pkg = glib.package_folder
            glib_bin = os.path.join(glib_pkg, "bin")
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
                    content = content.rstrip("\n") + "\n" + "\n".join(additions) + "\n"
                    save(self, glib_pc, content)

    def _get_pkg_config_path(self):
        """Build PKG_CONFIG_PATH from all dependency packages."""
        gen_dir = self.generators_folder
        paths = [gen_dir]
        for dep_name in ["glib", "pcre2", "libffi", "libxml2", "sqlite3",
                         "libaccounts-glib", "qt5-qtbase"]:
            dep = self.dependencies.get(dep_name)
            if not dep:
                continue
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                paths.append(pc_dir)
        return ":".join(paths)

    def build(self):
        apply_conandata_patches(self)
        self._fix_and_overlay_pkgconfig()

        # Find qmake from qt5-qtbase conan package
        qt = self.dependencies.get("qt5-qtbase")
        qt_pkg = qt.package_folder
        qmake = os.path.join(qt_pkg, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise Exception(f"qmake not found at {qmake}")

        # Set up environment for qmake using os.environ
        os.environ["PKG_CONFIG_PATH"] = self._get_pkg_config_path()
        os.environ["PATH"] = os.path.join(qt_pkg, "bin") + ":" + os.environ.get("PATH", "")

        # Run qmake from source folder
        src = self.source_folder
        pro_file = os.path.join(src, "accounts-qt.pro")
        self.run(f'cd "{src}" && "{qmake}" accounts-qt.pro -spec linux-clang '
                 f'"PREFIX=/" "LIBDIR=/lib"')

        # Build
        self.run(f'cd "{src}" && make -j2')

    def package(self):
        qt = self.dependencies.get("qt5-qtbase")
        qt_pkg = qt.package_folder
        os.environ["PKG_CONFIG_PATH"] = self._get_pkg_config_path()
        os.environ["PATH"] = os.path.join(qt_pkg, "bin") + ":" + os.environ.get("PATH", "")

        # Install using make install with INSTALL_ROOT
        self.run(f'make install INSTALL_ROOT="{self.package_folder}"')

    def package_info(self):
        self.cpp_info.libs = ["accounts-qt5"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "accounts-qt5")
