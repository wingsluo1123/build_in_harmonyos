#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5 — OHOS static build."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "The ncurses (new curses) library"
    license = "X11"
    homepage = "https://www.gnu.org/software/ncurses"
    url = "https://github.com/mirror/ncurses"

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
        tc.configure_args.append("--without-shared")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-cxx-binding")
        tc.configure_args.append("--enable-widec")
        tc.configure_args.append("--enable-overwrite")
        tc.generate()
        self._configure_args = tc.configure_args

    def build(self):
        # E160: Fix config.guess/sub for HarmonyOS detection
        self.run("sed -i '/case \$UNAME_SYSTEM in/a HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl ;;' config.guess", cwd=self.source_folder)
        self.run("sed -i 's/ironclad\*)/ironclad* | ohos*)/' config.sub", cwd=self.source_folder)
        self.run("sed -i 's/uclibc\*- )/uclibc*- | linux-ohos*- )/' config.sub", cwd=self.source_folder)
        autotools = Autotools(self)
        # HMDFS noexec: use /system/bin/sh to run configure, with --no-create
        configure_cmd = "/system/bin/sh ./configure --no-create " + " ".join(self._configure_args)
        self.run(configure_cmd, cwd=self.source_folder)
        # HMDFS noexec: patch config.status to use writable temp dir
        import tempfile, re, os as _os
        conf_tmp = tempfile.mkdtemp(dir='/storage/Users/currentUser', prefix='.ncurses-conf-')
        _os.chmod(conf_tmp, 0o755)
        cs_path = _os.path.join(self.source_folder, "config.status")
        if _os.path.isfile(cs_path):
            with open(cs_path, 'r') as f:
                cs_content = f.read()
            cs_content = re.sub(r'tmp=`\(umask 077 && mktemp -d[^`]+`', f'tmp="{conf_tmp}"', cs_content)
            cs_content = re.sub(r'tmp=\./conf\$\$-\$RANDOM', f'tmp={conf_tmp}', cs_content)
            with open(cs_path, 'w') as f:
                f.write(cs_content)
        self.run("/system/bin/sh ./config.status", cwd=self.source_folder)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "ncursesw")