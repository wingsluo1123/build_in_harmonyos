import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["pyqt-builder"].package_folder
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_pyqt_builder.py")
        import sys
        py = "/data/service/hnp/bin/python3" \
            if os.path.isfile("/data/service/hnp/bin/python3") \
            else sys.executable
        # import pyqtbuild -> sipbuild -> setuptools/packaging; the device
        # interpreter on the CI worker ships none of them globally.  Inject
        # every graph dependency's site-packages explicitly (in addition to
        # whatever the conanrun env aggregates) instead of assuming the
        # global interpreter has them.
        sites = []
        for name in ("sip", "setuptools", "packaging"):
            try:
                dep = self.dependencies[name]
            except Exception:
                continue
            if dep.package_folder:
                sites.append(os.path.join(dep.package_folder, "lib",
                                          "python3.12", "site-packages"))
        prefix = ""
        if sites:
            prefix = 'PYTHONPATH="%s:$PYTHONPATH" ' % os.pathsep.join(sites)
        self.run('%s"%s" "%s" "%s"' % (prefix, py, test_script, pkg),
                 env="conanrun")
