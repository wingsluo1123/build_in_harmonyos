#!/usr/bin/env python3
"""Conan test_package for kookbook 0.3.0.

Consumer-side verification of the *packaged* application. KookBook delivers
two GUI front-ends (bin/kookbook, bin/kookbooktouch) with no importable
library, so the consumer contract is the delivered executable plus its
runtime dependency closure. The real end-to-end case is implemented in
test_kookbook_e2e.py and executed here on the HarmonyOS PC target:

  E2E-KOOKBOOK-01 — "open a real recipe collection, scan and parse every
  recipe": the packaged bin/kookbook is launched under the offscreen QPA
  with an isolated HOME/XDG layout whose default collection
  (<HOME>/Documents/recipes, the location upstream opens when no user
  setting is present) contains real *.recipe.md recipes. The driver
  observes, with an inotify watch on that collection directory, that the
  running application opens and reads every recipe file, i.e. that the
  real business flow (Scanner::setRootPath -> parseThingsInDifferentThread
  -> RecipeParser::parseRecipe) consumed the real business input.

See test_package/MANIFEST.yml for the upstream test inventory and the
reproduction entry point (test_app.sh).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class KookbookTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        assert dep.package_folder, "kookbook package folder missing"
        app_bin = os.path.join(dep.package_folder, "bin", "kookbook")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"
        assert os.access(app_bin, os.X_OK), f"packaged application not executable: {app_bin}"

        # The driver creates its own isolated HOME/XDG tree under $TMPDIR and
        # exports it to the application, so no run directories are created
        # here (leaving none of them behind in the recipe source folder).
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
        for p in self.dependencies.values():
            if p and p.package_folder:
                lib_dir = os.path.join(p.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins_dir = os.path.join(p.package_folder, "plugins")
                if os.path.isdir(plugins_dir):
                    env.prepend_path("QT_PLUGIN_PATH", plugins_dir)

        driver = os.path.join(self.source_folder, "test_kookbook_e2e.py")
        fixtures = os.path.join(self.source_folder, "fixtures")
        with env.vars(self).apply():
            self.run(
                'python3 "{}" "{}" "{}"'.format(driver, app_bin, fixtures),
                env="conanrun",
            )
