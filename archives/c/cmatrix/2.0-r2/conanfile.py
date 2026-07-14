from conan import ConanFile
from conan.tools.files import copy, get, rmdir
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain

import os
import shutil


class CmatrixRecipe(ConanFile):
    name = "cmatrix"
    version = "2.0-r2"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"
    generators = ()
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    description = "Classic terminal screensaver for the console"
    topics = ("terminal", "screensaver", "ncurses")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-shared",
            "--enable-widec",
            "--enable-overwrite",
        ])
        tc.generate()

    def build(self):
        build_src = os.path.join(self.build_folder, "src")
        if os.path.exists(build_src):
            shutil.rmtree(build_src)
        shutil.copytree(self.source_folder, build_src, dirs_exist_ok=True)

        for root, dirs, files in os.walk(build_src):
            os.chmod(root, 0o755)
            for name in dirs:
                os.chmod(os.path.join(root, name), 0o755)
            for name in files:
                path = os.path.join(root, name)
                mode = 0o755 if os.access(path, os.X_OK) else 0o644
                os.chmod(path, mode)

        recipe_folder = os.path.join(build_src, "cmatrix-2.0")
        self.run("autoreconf -fi", cwd=recipe_folder)
        self.run("./configure --prefix=$PWD/pkg --without-shared --enable-widec --enable-overwrite", cwd=recipe_folder)
        self.run("make -j$(nproc)", cwd=recipe_folder)

    def package(self):
        build_src = os.path.join(self.build_folder, "src", "cmatrix-2.0")
        self.run(f"make install DESTDIR={self.package_folder}", cwd=build_src)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        rmdir(self, os.path.join(self.package_folder, "share", "info"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
