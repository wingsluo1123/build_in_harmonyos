#!/usr/bin/env python3
"""Conan recipe for fcheck 2.7.59 — pure Perl filesystem baseline integrity checker.

fcheck is a pure Perl script that monitors directory files for additions, deletions,
and modifications. It has no C/C++ compilation step; it is installed as a standalone
Perl script with a configuration file.

Platform adaptations for OHOS:
  1. Shebang fix: #!/usr/bin/perl → keep as-is (perl may be at /usr/bin/perl or
     /data/service/hnp/bin/perl on OHOS; the conanrun env must ensure perl is in PATH)
  2. Default config path: changed from /usr/local/admtools/conf/fcheck.cfg to
     a packaged location under package_folder/etc/fcheck/fcheck.cfg
  3. Logger path: /usr/bin/logger — must exist on OHOS or be configured otherwise
  4. FileTyper: /bin/file — must exist on OHOS or user provides alternative path
  5. Hash tool: default changed from /bin/cksum to /usr/bin/sha256sum in Debian patches;
     we ship cksum as the default for wider compatibility

R32: OHOS 适配通过 shebang 保留 /usr/bin/perl，由 conanrun 环境保证 perl 可执行。
R28: test_package/ exists.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FcheckConan(ConanFile):
    name = "fcheck"
    version = "2.7.59"
    description = "Filesystem baseline integrity checker (Perl script)"
    license = "GPL-2.0-or-later"
    homepage = "http://web.archive.org/web/20050415074059/www.geocities.com/fcheck2000/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # --- Platform adaptation: fix default config path ---
        # The script hardcodes $config="/usr/local/admtools/conf/fcheck.cfg"
        # which is not appropriate for a packaged installation.
        # We patch it to use the packaged config location.
        fcheck_path = os.path.join(self.source_folder, "fcheck")
        if os.path.isfile(fcheck_path):
            with open(fcheck_path, "r") as f:
                content = f.read()
            old_config = '/usr/local/admtools/conf/fcheck.cfg'
            new_config = os.path.join(self.package_folder, 'etc', 'fcheck', 'fcheck.cfg')
            if old_config in content:
                content = content.replace(old_config, new_config, 1)
                with open(fcheck_path, "w") as f:
                    f.write(content)
                self.output.info(f"Fixed config path: {old_config} -> {new_config}")

        # --- Ensure executable bit ---
        if os.path.isfile(fcheck_path):
            st = os.stat(fcheck_path)
            os.chmod(fcheck_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        # Install the fcheck script to bin/
        copy(self, "fcheck", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # Install the default configuration file to etc/fcheck/
        copy(self, "fcheck.cfg", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc", "fcheck"), keep_path=False)

        # Install README and license to doc/
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "doc", "fcheck"), keep_path=False)
        copy(self, "license", src=self.source_folder,
             dst=os.path.join(self.package_folder, "doc", "fcheck"), keep_path=False)

        # Ensure scripts are executable
        bin_dir = os.path.join(self.package_folder, "bin")
        for fname in os.listdir(bin_dir):
            fpath = os.path.join(bin_dir, fname)
            if os.path.isfile(fpath):
                os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # Pure Perl script: no libraries, just executable in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
