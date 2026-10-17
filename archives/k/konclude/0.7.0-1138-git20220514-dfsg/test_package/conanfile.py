#!/usr/bin/env python3
"""Consumer test package for konclude on HarmonyOS PC.

Rule 12 (赛事成功适配类要求): at least one *complete consumer end-to-end case*
must really run on the HarmonyOS PC target and assert a real business result.
This test package is that consumer.  It never touches the source tree: the
binary, the OWL fixtures and the OWLlink request it drives are resolved from the
**installed** package and from this test_package folder only.

Two cases are executed by ``test_consumer.py`` (see that file for the detailed
step-by-step flow and the assertion inventory):

  CONSUMER-E2E-01  real OWL 2 XML inputs -> installed ``Konclude``
                   (classification / satisfiability / consistency) -> inferred
                   class hierarchy + answer strings are asserted.
  CONSUMER-E2E-02  installed ``Konclude owllinkserver`` on TCP loopback ->
                   real OWLlink XML request -> HTTP 200 + business answer
                   (``BooleanResponse result="false"``) asserted.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # Native OHOS build (build == host == target); a cross build could not
            # execute this consumer, which the report would have to declare.
            raise ConanException(
                "konclude consumer test requires a runnable OHOS/aarch64 target"
            )

        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "Konclude")
        if not os.path.isfile(binary):
            raise ConanException(f"installed package does not provide bin/Konclude: {binary}")

        script = os.path.join(self.recipe_folder, "test_consumer.py")
        fixtures = os.path.join(self.recipe_folder, "fixtures")
        for path in (script, fixtures):
            if not os.path.exists(path):
                raise ConanException(f"consumer test asset missing: {path}")

        command = (f"python3 {shlex.quote(script)} "
                   f"--konclude {shlex.quote(binary)} "
                   f"--fixtures {shlex.quote(fixtures)}")
        # env="conanrun" provides LD_LIBRARY_PATH for the Qt5 runtime the
        # installed Konclude links against.
        self.run(command, env="conanrun")
