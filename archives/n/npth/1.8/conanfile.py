from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir, save, load
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class NpthConan(ConanFile):
    name = "npth"
    version = "1.8"
    description = "GNU Portable Threads library — lightweight threading based on pthread"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass  # npth only depends on pthread (system-provided)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--prefix=")
        tc.generate()

    def _fix_hmdfs_tmpdir(self, content):
        """Fix HMDFS filesystem issues with config.status temp directories.

        Two problems on HarmonyOS:
        1. HMDFS does not allow creating temp dirs in the current directory (./)
        2. The process UID differs from the file owner UID, so umask 077
           creates directories the process cannot write to
        """
        # Use TMPDIR instead of current directory for temp files
        content = content.replace(
            'mktemp -d "./confXXXXXX"',
            'mktemp -d "${TMPDIR:-/storage/Users/currentUser/tmp}/confXXXXXX"'
        )
        content = content.replace(
            'tmp=./conf$$-$RANDOM',
            'tmp=${TMPDIR:-/storage/Users/currentUser/tmp}/conf$$-$RANDOM'
        )
        # Remove umask 077 from mktemp calls so the directory gets group/other
        # execute permissions (needed because process UID != file owner UID on HMDFS)
        content = content.replace(
            'umask 077 && mktemp -d',
            'mktemp -d'
        )
        return content

    def build(self):
        apply_conandata_patches(self)

        # Fix configure script for HMDFS before running configure
        if self.settings.os == "OHOS":
            configure_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(configure_path):
                content = load(self, configure_path)
                content = self._fix_hmdfs_tmpdir(content)
                save(self, configure_path, content)

        autotools = Autotools(self)
        autotools.configure()

        # Also fix config.status after configure creates it
        if self.settings.os == "OHOS":
            config_status_path = os.path.join(self.source_folder, "config.status")
            if os.path.exists(config_status_path):
                content = load(self, config_status_path)
                content = self._fix_hmdfs_tmpdir(content)
                save(self, config_status_path, content)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["npth"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
