import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class Icu4CConan(ConanFile):
    name = "icu4c"
    version = "78"
    description = "International Components for Unicode - Unicode and globalization support library"
    license = "Unicode/ICU License"
    homepage = "https://icu.unicode.org/"
    url = "https://github.com/unicode-org/icu"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_icuio": [True, False],
        "with_extras": [True, False],
    }
    default_options = {
        "shared": False,
        "with_icuio": True,
        "with_extras": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--with-data-packaging=static")
        tc.configure_args.append("--disable-tests")
        tc.configure_args.append("--disable-samples")
        if not self.options.with_icuio:
            tc.configure_args.append("--disable-icuio")
        if not self.options.with_extras:
            tc.configure_args.append("--disable-extras")
        tc.generate()

        # Set environment for HarmonyOS: TMPDIR for temp files,
        # and cache build/host type to skip config.guess failure
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.define("ac_cv_build", "aarch64-unknown-linux-gnu")
        env.define("ac_cv_host", "aarch64-unknown-linux-gnu")
        env.define("ac_cv_target", "aarch64-unknown-linux-gnu")
        env.vars(self, scope="build").save_script("icu_env")

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")

        # Create tmp dir for configure's temp files
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # E165: Fix shebangs for HarmonyOS
        for f in ["configure", "install-sh", "mkinstalldirs", "config.guess", "config.sub"]:
            fpath = os.path.join(source_dir, f)
            if os.path.exists(fpath):
                replace_in_file(self, fpath, "#! /bin/sh", "#! /system/bin/sh", strict=False)
                replace_in_file(self, fpath, "#!/bin/sh", "#!/system/bin/sh", strict=False)
                replace_in_file(self, fpath, "#! /bin/bash", "#! /data/service/hnp/bin/bash", strict=False)
                replace_in_file(self, fpath, "#!/bin/bash", "#!/data/service/hnp/bin/bash", strict=False)

        # Fix config.status temp dir issue (E002: HMDFS doesn't allow file creation in mktemp dirs)
        configure_path = os.path.join(source_dir, "configure")
        conf_tmpdir = os.path.join(tmpdir, "icu-conf")
        os.makedirs(conf_tmpdir, exist_ok=True)
        if os.path.exists(configure_path):
            # Replace mktemp with fixed dir: use sed-style replacement that preserves shell syntax
            # Original: tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
            # Fixed: tmp=FIXED_DIR &&
            replace_in_file(self, configure_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                'tmp="' + conf_tmpdir + '" &&',
                strict=False)
            replace_in_file(self, configure_path,
                '  tmp=./conf$$-$RANDOM',
                '  tmp="' + conf_tmpdir + '"',
                strict=False)

        # Create missing rules.mk
        rules_mk = os.path.join(source_dir, "data", "rules.mk")
        if not os.path.exists(rules_mk):
            save(self, rules_mk, "")

        # Run configure from source/ subdirectory
        autotools = Autotools(self)
        autotools.configure(build_script_folder="source")

        # Fix generated config.status to use fixed temp dir
        cs_path = os.path.join(source_dir, "config.status")
        if os.path.exists(cs_path):
            replace_in_file(self, cs_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                'tmp="' + conf_tmpdir + '" &&',
                strict=False)
            replace_in_file(self, cs_path,
                '  tmp=./conf$$-$RANDOM',
                '  tmp="' + conf_tmpdir + '"',
                strict=False)
            # Set ac_tmp directly
            replace_in_file(self, cs_path,
                'tmp= ac_tmp=',
                'tmp=' + conf_tmpdir + ' ac_tmp=' + conf_tmpdir,
                strict=False)
            # Re-run config.status
            self.run(f'cd "{source_dir}" && TMPDIR="{tmpdir}" /system/bin/sh ./config.status', env="conanbuild")

        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["icuuc", "icui18n", "icudata"]
        if self.options.with_icuio:
            self.cpp_info.libs.append("icuio")
        self.cpp_info.libs.append("icutu")
        self.cpp_info.set_property("cmake_file_name", "ICU")
        self.cpp_info.set_property("pkg_config_name", "icu-uc")
        self.cpp_info.system_libs = ["c++"]
