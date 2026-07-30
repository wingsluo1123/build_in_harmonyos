from conan import ConanFile


class Dex2JarTestPkgConan(ConanFile):
    python_requires = "common/[>=1.0]"
    python_requires_extend = "common.CommonTest"
    default_options = "*:shared=False"

    def requirements(self):
        self.tool_requires(self.tested_reference_str)
