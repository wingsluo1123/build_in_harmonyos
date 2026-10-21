import os

from conan import ConanFile
from conan.tools.build import can_run


class WikiTuiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_wiki_tui.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("not runnable on this host — skipping runtime test")
            return

        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_wiki_tui.sh")

        # 必须用 self.run(...)（CI 门禁 L0d 静态检查要求）；
        # self.run 同时应用 conanrun 运行期环境。
        self.run(f'sh "{script}" "{pkg_folder}"', env="conanrun")
