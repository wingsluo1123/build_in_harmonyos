import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        xml = os.path.join(dep.cpp_info.resdirs[0], "indi", "indi_lunatico.xml")
        # the INDI core libraries the drivers link against live in libindi's package
        indi = self.dependencies["libindi"]
        indi_libdir = os.path.join(indi.package_folder, indi.cpp_info.libdirs[0])
        # 上游把 udev 规则装到绝对路径 /usr/lib/udev/rules.d，本配方重定向进私有前缀
        rules = os.path.join(dep.cpp_info.libdirs[0], "udev", "rules.d",
                             "99-armadilloplatypus.rules")

        test_dir = self.source_folder
        if not os.path.exists(os.path.join(test_dir, "check_all_drivers.py")):
            test_dir = self.recipe_folder
        checker = os.path.join(test_dir, "check_all_drivers.py")

        argv = [sys.executable, checker, bindir, xml, indi_libdir, rules]
        self.run(" ".join('"%s"' % item for item in argv), env="conanrun")
