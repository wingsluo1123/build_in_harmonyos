import os
import shlex
import shutil
import configparser

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Qt5Qt3dConan(ConanFile):
    name = "qt5-qt3d"
    version = "5.15.2"
    description = "Qt5 3D rendering module for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://github.com/qt/qt3d"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        # Download qt3d source
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get_kwargs = {"url": url, "strip_root": True}
                if source_data.get("sha256"):
                    get_kwargs["sha256"] = source_data["sha256"]
                get(self, **get_kwargs)
                break
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        else:
            raise ConanInvalidConfiguration("Unable to download source from all mirrors")

        # Download qt5-qtdeclarative source (not available as Conan package;
        # built from source to provide Qt5Qml/Qt5Quick for Quick3D modules).
        qtdecl_data = self.conan_data["qtdeclarative_sources"][self.version]
        qtdecl_urls = qtdecl_data["url"]
        if isinstance(qtdecl_urls, str):
            qtdecl_urls = [qtdecl_urls]
        qtdecl_dest = os.path.join(self.source_folder, "qtdeclarative_src")
        os.makedirs(qtdecl_dest, exist_ok=True)
        for url in qtdecl_urls:
            try:
                get_kwargs = {"url": url, "strip_root": True,
                              "destination": qtdecl_dest}
                if qtdecl_data.get("sha256"):
                    get_kwargs["sha256"] = qtdecl_data["sha256"]
                get(self, **get_kwargs)
                break
            except ConanException as error:
                self.output.warning(
                    f"Failed to download qtdeclarative source from {url}: {error}"
                )
        else:
            raise ConanInvalidConfiguration(
                "Unable to download qtdeclarative source from all mirrors"
            )

    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder
        qtbase_bin = os.path.join(qtbase_pkg, "bin")
        qmake = os.path.join(qtbase_bin, "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")

        # Create combined Qt5 directory with qt5-qtbase files
        combined_dir = os.path.join(self.build_folder, "qt5_combined")
        os.makedirs(combined_dir, exist_ok=True)
        for subdir in ("bin", "lib", "include", "mkspecs", "plugins", "src"):
            src = os.path.join(qtbase_pkg, subdir)
            dst = os.path.join(combined_dir, subdir)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst, symlinks=True)

        # Write corrected qt.conf
        qt_conf = os.path.join(combined_dir, "bin", "qt.conf")
        os.makedirs(os.path.dirname(qt_conf), exist_ok=True)
        with open(qt_conf, "w", encoding="utf-8") as f:
            f.write(
                "[EffectivePaths]\nPrefix=..\n"
                "[Paths]\nPrefix=..\n"
                "HostPrefix=..\n"
                "HostData=.\n"
                "Sysroot=\nSysrootifyPrefix=false\n"
                "TargetSpec=linux-clang\nHostSpec=linux-clang\n"
            )

        # Create symlinks from old build-time QT_HOST_DATA path to combined dir
        qtbase_qt_conf = os.path.join(qtbase_bin, "qt.conf")
        if os.path.isfile(qtbase_qt_conf):
            cfg = configparser.ConfigParser()
            cfg.read(qtbase_qt_conf)
            qtbase_prefix = cfg.get("Paths", "Prefix", fallback="")
            if qtbase_prefix and os.path.isabs(qtbase_prefix):
                build_root = os.path.dirname(qtbase_prefix)
                old_build_dir = os.path.join(build_root, "b")
                old_mkspecs = os.path.join(old_build_dir, "mkspecs")
                if not os.path.exists(old_mkspecs):
                    os.makedirs(old_mkspecs, exist_ok=True)
                for sub in ("modules-inst", "features", "modules"):
                    src_link = os.path.join(old_mkspecs, sub)
                    dst_link = os.path.join(combined_dir, "mkspecs", sub)
                    if os.path.isdir(dst_link):
                        if os.path.islink(src_link) or os.path.exists(src_link):
                            os.remove(src_link)
                        os.symlink(dst_link, src_link)
                for sub in ("include", "lib", "src", "bin"):
                    src_link = os.path.join(old_build_dir, sub)
                    dst_link = os.path.join(combined_dir, sub)
                    if os.path.isdir(dst_link):
                        if os.path.islink(src_link) or os.path.exists(src_link):
                            os.remove(src_link)
                        os.symlink(dst_link, src_link)

        combined_qmake = os.path.join(combined_dir, "bin", "qmake")
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)

        build_env = Environment()
        if cc:
            build_env.define("CC", cc)
        if cxx:
            build_env.define("CXX", cxx)
        build_env.prepend_path("PATH", os.path.join(combined_dir, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(combined_dir, "lib"))

        with build_env.vars(self).apply():
            # Build qt5-qtdeclarative from source
            qtdecl_src = os.path.join(self.source_folder, "qtdeclarative_src")
            self.run(
                f'cd "{qtdecl_src}" && {shlex.quote(combined_qmake)} '
                f'qtdeclarative.pro "QT_BUILD_PARTS=libs tools"'
            )
            self.run(
                f'cd "{qtdecl_src}" && make -j{jobs} QMAKE_STRIP=""'
            )
            self.run(f'cd "{qtdecl_src}" && make install')

            # Build qt5-qt3d
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(combined_qmake)} '
                f'qt3d.pro "QT_BUILD_PARTS=libs tools"'
            )
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""'
            )

    def package(self):
        src = self.source_folder
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.prl", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # QML plugins
        qml_dir = os.path.join(src, "qml")
        if os.path.isdir(qml_dir):
            copy(self, "*", src=qml_dir,
                 dst=os.path.join(self.package_folder, "qml"), keep_path=True)
        # Render plugins
        plugins_dir = os.path.join(src, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)
        # Source headers referenced by forwarding includes
        src_headers = os.path.join(src, "src")
        if os.path.isdir(src_headers):
            copy(self, "*.h", src=src_headers,
                 dst=os.path.join(self.package_folder, "src"), keep_path=True)
        # Bin tools
        bin_dir = os.path.join(src, "bin")
        if os.path.isdir(bin_dir):
            copy(self, "*", src=bin_dir,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = [
            "Qt53DCore", "Qt53DRender", "Qt53DInput", "Qt53DLogic",
            "Qt53DAnimation", "Qt53DExtras",
            "Qt53DQuick", "Qt53DQuickRender", "Qt53DQuickInput",
            "Qt53DQuickAnimation", "Qt53DQuickExtras", "Qt53DQuickScene2D",
        ]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui"]
        self.cpp_info.set_property("cmake_file_name", "Qt53D")
        self.cpp_info.set_property("cmake_target_name", "Qt5::3DCore")
