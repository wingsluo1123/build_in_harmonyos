import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Qt5QtgraphicaleffectsConan(ConanFile):
    name = "qt5-qtgraphicaleffects"
    version = "5.15.2"
    description = "Qt5 GraphicalEffects QML module for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://github.com/qt/qtgraphicaleffects"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.1")
        self.requires("qt5-qtdeclarative/5.15.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256", ""), strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qtbase_dir = qtbase.package_folder
        qtdecl_dir = qtdecl.package_folder
        qmake = os.path.join(qtbase_dir, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        # Fix qt.conf so qmake resolves modules in the conan package path
        qt_conf = os.path.join(qtbase_dir, "bin", "qt.conf")
        with open(qt_conf, "w") as f:
            f.write("[Paths]\n")
            f.write(f"Prefix={qtbase_dir}\n")
            f.write(f"HostPrefix={qtbase_dir}\n")
            f.write("Sysroot=\n")
            f.write("SysrootifyPrefix=false\n")
            f.write("TargetSpec=linux-clang\n")
            f.write("HostSpec=linux-clang\n")

        # Merge qtdeclarative files into qtbase directory so qmake finds all modules
        for subdir in ["lib", "include", "qml", "mkspecs/modules"]:
            src_dir = os.path.join(qtdecl_dir, subdir)
            dst_dir = os.path.join(qtbase_dir, subdir)
            if not os.path.isdir(src_dir):
                continue
            os.makedirs(dst_dir, exist_ok=True)
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                if os.path.exists(dst_path):
                    continue
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                elif os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)

        build_env = Environment()
        build_env.define("QTDIR", qtbase_dir)
        build_env.prepend_path("PATH", os.path.join(qtbase_dir, "bin"))
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang qtgraphicaleffects.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs}')

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # QML plugin files are installed to qml/QtGraphicalEffects/
        copy(self, "*.so*", src=os.path.join(src, "qml"),
             dst=os.path.join(pkg, "qml"), keep_path=True)
        copy(self, "*.qml", src=os.path.join(src, "qml"),
             dst=os.path.join(pkg, "qml"), keep_path=True)
        copy(self, "qmldir", src=os.path.join(src, "qml"),
             dst=os.path.join(pkg, "qml"), keep_path=True)
        copy(self, "plugins.qmltypes", src=os.path.join(src, "qml"),
             dst=os.path.join(pkg, "qml"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["qml/QtGraphicalEffects", "qml/QtGraphicalEffects/private"]
        self.cpp_info.includedirs = []
        # QtGraphicalEffects is a pure QML module (no C++ link libraries)
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui"]
        self.cpp_info.set_property("cmake_file_name", "Qt5GraphicalEffects")
        self.cpp_info.set_property("cmake_target_name", "Qt5::GraphicalEffects")
