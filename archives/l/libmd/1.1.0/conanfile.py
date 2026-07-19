#!/usr/bin/env python3
"""Conan recipe for libmd 1.1.0.
OHOS 上 HMDFS 禁止执行用户文件 (E046)，config.status 创建临时 awk 脚本会失败。
解决：configure 后在 config.status 中用 $AWK -f 替换直接执行。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmdConan(ConanFile):
    name = "libmd"
    version = "1.1.0"
    description = "Message Digest functions from BSD systems"
    license = "BSD-3-Clause"
    homepage = "https://libbsd.freedesktop.org"
    url = "https://libbsd.freedesktop.org/releases/libmd-1.1.0.tar.xz"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        arch_map = {"armv8": "aarch64", "armv8_32": "aarch64", "x86_64": "x86_64", "x86": "i386"}
        build_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        tc.configure_args.append(f"--build={build_arch}-unknown-linux-ohos")
        tc.generate()
        self._configure_args = tc.configure_args

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # HMDFS noexec: use /system/bin/sh to run configure, with --no-create
        configure_cmd = "/system/bin/sh ./configure --no-create " + " ".join(self._configure_args)
        self.run(configure_cmd, cwd=self.source_folder)
        # HMDFS noexec: patch config.status to use writable temp dir
        import tempfile, re, os
        conf_tmp = tempfile.mkdtemp(dir='/storage/Users/currentUser', prefix='.libmd-conf-')
        os.chmod(conf_tmp, 0o755)
        cs_path = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(cs_path):
            with open(cs_path, 'r') as f:
                cs_content = f.read()
            cs_content = re.sub(r'tmp=`\(umask 077 && mktemp -d[^`]+`', f'tmp="{conf_tmp}"', cs_content)
            cs_content = re.sub(r'tmp=\./conf\$\$-\$RANDOM', f'tmp={conf_tmp}', cs_content)
            with open(cs_path, 'w') as f:
                f.write(cs_content)
        self.run("/system/bin/sh ./config.status", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install DESTDIR={} -j1".format(self.package_folder), cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["md"]
        self.cpp_info.set_property("pkg_config_name", "libmd")