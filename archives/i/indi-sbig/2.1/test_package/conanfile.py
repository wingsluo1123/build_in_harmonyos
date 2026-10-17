import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    """Consumer end-to-end checks against the packaged indi-sbig driver."""
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libindi/2.2.2.1")
        self.requires("libusb/1.0.27")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        xml = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0],
                           "indi", "indi_sbig.xml")
        indi = self.dependencies["libindi"]
        indi_libdir = os.path.join(indi.package_folder, indi.cpp_info.libdirs[0])
        usb = self.dependencies["libusb"]
        usb_libdir = os.path.join(usb.package_folder, usb.cpp_info.libdirs[0])

        test_dir = self.source_folder
        if not os.path.exists(os.path.join(test_dir, "check_driver.py")):
            test_dir = self.recipe_folder
        checker = os.path.join(test_dir, "check_driver.py")

        argv = [sys.executable, checker, bindir, xml, indi_libdir, usb_libdir]
        self.run(" ".join('"%s"' % item for item in argv), env="conanrun")
