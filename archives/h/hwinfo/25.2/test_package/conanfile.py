import os
import glob

from conan import ConanFile


class HwinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must actually exercise the package
        # hwinfo is a command-line tool; run it to verify the package works
        # Set up LD_LIBRARY_PATH for both libhd (from package) and libuuid (system)
        pkg = self.dependencies["hwinfo"].package_folder
        lib_dir = os.path.join(pkg, "lib")
        bin_dir = os.path.join(pkg, "bin")
        uuid_so = glob.glob("/data/service/hnp/**/libuuid.so*", recursive=True)
        uuid_dir = os.path.dirname(uuid_so[0]) if uuid_so else ""
        extra_ld = ":".join(filter(None, [lib_dir, uuid_dir]))
        os.environ["LD_LIBRARY_PATH"] = extra_ld + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        hwinfo_bin = os.path.join(bin_dir, "hwinfo")
        self.run(f'"{hwinfo_bin}" --version')
