from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class Mpg123Conan(ConanFile):
    name = "mpg123"
    version = "1.33.5"
    description = "mpg123 - fast console MPEG audio player/decoder library"
    license = "LGPL-2.1-or-later"
    url = "https://www.mpg123.de"
    homepage = "https://www.mpg123.de"
    topics = ("audio", "mp3", "decoder", "mpeg")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            "https://www.mpg123.de/download/mpg123-1.33.5.tar.bz2",
            sha256="0d7ebc8da0aff3ca383c8c6b5a6adbe402ee5bb256685b8c5499f3a739f9d6dd",
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--disable-modules",
        ])
        tc.generate()

    def build(self):
        # --- Patch config.guess for HarmonyOS ---
        # On HarmonyOS, `uname -s` returns "HarmonyOS" which config.guess
        # (version 2022) does not recognize. Add it to the Linux|GNU case
        # so that LIBC detection runs and the aarch64:Linux case matches.
        config_guess = os.path.join(self.source_folder, "build", "config.guess")
        if os.path.exists(config_guess):
            # Override HarmonyOS to Linux so config.guess recognizes the system
            # and enters the LIBC detection block. The main case at line 193
            # matches aarch64:Linux:*:* and outputs aarch64-unknown-linux-gnu.
            replace_in_file(
                self,
                config_guess,
                "case $UNAME_SYSTEM in",
                'if [ "$UNAME_SYSTEM" = "HarmonyOS" ]; then\n\tUNAME_SYSTEM=Linux\nfi\ncase $UNAME_SYSTEM in',
            )
            # Fix umask 077 -> 022 in config.guess too (for temp dir creation)
            replace_in_file(
                self,
                config_guess,
                "umask 077",
                "umask 022",
            )

        # --- Patch config.sub to accept 'ohos' as valid OS ---
        config_sub = os.path.join(self.source_folder, "build", "config.sub")
        if os.path.exists(config_sub):
            # Add ohos* to the accepted OS list (after fiwix*)
            replace_in_file(
                self,
                config_sub,
                "| fiwix* )",
                "| fiwix* | ohos* )",
            )
            # Add linux-ohos* to the kernel-os validation
            replace_in_file(
                self,
                config_sub,
                "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\",
                "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* | linux-ohos* \\",
            )

        # --- Fix umask in configure for HMDFS ---
        # HMDFS with umask 077 creates files with 600 permissions, causing
        # build failures. Change to umask 022 (644 files, 755 dirs).
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            replace_in_file(
                self,
                configure,
                "umask 077",
                "umask 022",
            )

        # --- Run configure and make ---
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        # Headers
        copy(
            self,
            pattern="*.h",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "src", "include"),
            keep_path=False,
        )
        # Static libraries - check multiple possible locations
        for lib_dir in [
            os.path.join(self.build_folder, "src", ".libs"),
            os.path.join(self.build_folder, "src", "libmpg123", ".libs"),
            os.path.join(self.build_folder, ".libs"),
        ]:
            copy(
                self,
                pattern="*.a",
                dst=os.path.join(self.package_folder, "lib"),
                src=lib_dir,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mpg123")
        self.cpp_info.set_property("cmake_target_name", "mpg123::mpg123")
        self.cpp_info.libs = ["mpg123"]
