import os
import re
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download, export_conandata_patches,
                               load, save)
from conan.tools.layout import basic_layout


class TpasteConan(ConanFile):
    name = "tpaste"
    version = "0.8"
    description = "Helper script to paste stdin to https://tpaste.us (POSIX sh wrapper around curl)"
    license = "GPL-2.0-only"
    homepage = "https://tpaste.us"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)  # 本版本无补丁，沿用统一模板

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # tpaste 运行时 exec curl
        self.requires("curl/8.15.0")

    def source(self):
        source = self.conan_data["sources"][self.version]
        download(self, source["url"], os.path.join(self.source_folder, "APKBUILD"),
                 sha256=source["sha256"])
        license_file = self.conan_data["license_file"]
        download(self, license_file["url"], os.path.join(self.source_folder, "COPYING"),
                 sha256=license_file["sha256"])

    @staticmethod
    def _configure_shell():
        for candidate in (os.environ.get("CONFIG_SHELL"), shutil.which("sh")):
            if candidate and os.path.exists(candidate):
                return candidate
        raise ConanInvalidConfiguration("A POSIX sh executable is required")

    def build(self):
        apply_conandata_patches(self)
        # 上游 APKBUILD 的 package() 以 printf 生成 /usr/bin/tpaste，
        # 这里按同一模板（pkgver 与 url 取自 APKBUILD）生成同样的脚本。
        apkbuild = load(self, os.path.join(self.source_folder, "APKBUILD"))
        pkgver = re.search(r'^pkgver=(\S+)$', apkbuild, re.M)
        url = re.search(r'^url="(https://[A-Za-z0-9.\-]+)"$', apkbuild, re.M)
        if not pkgver or pkgver.group(1) != self.version or not url:
            raise ConanInvalidConfiguration("Unexpected APKBUILD content")
        script = os.path.join(self.build_folder, "tpaste")
        save(self, script,
             "#!/bin/sh\n\nexec curl -sSF 'tpaste=<-' " + url.group(1))
        self.run(f'"{self._configure_shell()}" -n "{script}"')

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "tpaste", src=self.build_folder, dst=bindir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        script = os.path.join(bindir, "tpaste")
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
