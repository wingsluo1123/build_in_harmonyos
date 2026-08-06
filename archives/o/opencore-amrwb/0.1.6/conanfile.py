from conan import ConanFile
from conan.tools.files import get, rm, rmdir, replace_in_file
from conan.tools.gnu import AutotoolsToolchain, Autotools
import os


class OpencoreAmrwbConan(ConanFile):
    name = "opencore-amrwb"
    version = "0.1.6"
    description = "OpenCORE AMR-WB: Adaptive Multi-Rate Wideband speech codec library"
    license = "Apache-2.0"
    homepage = "https://sourceforge.net/projects/opencore-amr/"
    topics = ("amr", "audio", "codec", "speech", "wideband")

    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._patch_config_files()

    def _patch_config_files(self):
        # Patch config.guess to support HarmonyOS platform
        config_guess = os.path.join(self.source_folder, "config.guess")
        # Add HarmonyOS case before Linux in the LIBC detection section
        replace_in_file(
            self, config_guess,
            "Linux|GNU|GNU/*)",
            "HarmonyOS)\n\tLIBC=ohos\n\t;;\nLinux|GNU|GNU/*)",
        )
        # Add aarch64:HarmonyOS case before aarch64:Linux case
        replace_in_file(
            self, config_guess,
            "    aarch64:Linux:*:*)",
            "    aarch64:HarmonyOS:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n\t;;\n    aarch64:Linux:*:*)",
        )

        # Patch config.sub to support ohos OS
        config_sub = os.path.join(self.source_folder, "config.sub")
        # Add ohos* to OS recognition list
        replace_in_file(
            self, config_sub,
            "| fiwix* )",
            "| fiwix* | ohos* )",
        )
        # Add linux-ohos* to kernel-OS validation
        replace_in_file(
            self, config_sub,
            "| linux-musl* | linux-relibc* | linux-uclibc* )",
            "| linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )",
        )

        # Fix umask for HarmonyOS: umask 077 creates dirs with drwx--S---
        # (setgid without group execute), which prevents file creation on HMDFS.
        # Changing to umask 027 gives drwxr-s--- (setgid with group execute).
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 027")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
        ])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # The project compiles .cpp files as C (--enable-compile-c is the default).
        # The Conan CXXFLAGS from the profile include -std=c++17 and -stdlib=libc++,
        # which conflict with the -x c -std=c99 flags used for C compilation.
        # Override CXXFLAGS on the make command line to use only C-compatible flags.
        # -j1 avoids make jobserver mkfifo issues on HarmonyOS (EOPNOTSUPP).
        autotools.make(args=["-j1", "CXXFLAGS=-O3"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove amrnb files - this package only contains amrwb
        rm(self, "libopencore-amrnb*", os.path.join(self.package_folder, "lib"))
        rm(self, "opencore-amrnb.pc", os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "include", "opencore-amrnb"))
        # Remove libtool files and pkgconfig
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["opencore-amrwb"]
        self.cpp_info.set_property("cmake_file_name", "opencore-amrwb")
        self.cpp_info.set_property("cmake_target_name", "opencore_amrwb::opencore_amrwb")
