import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibngfQtConan(ConanFile):
    name = "libngf-qt"
    version = "0.3.1"
    description = "Qt bindings for the NGF (Notified Globally) notifications daemon"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/nemomobile/libngf-qt"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 依赖 qt5-qtbase/5.15.2.1：Qt5 库需要 qt5-qtbase
        # 提供的 Qt5 基础库与 qmake 工具
        self.requires("qt5-qtbase/5.15.2.1")

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
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.1 does not provide the required bin/qmake tool"
            )
        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        with build_env.vars(self).apply():
            self.run(f'cd "{self.source_folder}" && {shlex.quote(qmake)} libngf-qt.pro')
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs}')

    def package(self):
        src = self.source_folder
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.prl", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ngf-qt"]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core"]
        self.cpp_info.set_property("cmake_file_name", "NGF-Qt")
        self.cpp_info.set_property("cmake_target_name", "NGF::Qt")
