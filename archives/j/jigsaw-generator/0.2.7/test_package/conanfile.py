# test_package for jigsaw-generator 0.2.7 — consumer-side verification.
"""
The artifact is pure Python (no architecture-specific code), so "can run on
the host" does not depend on the target architecture: it only needs python3 +
PyYAML. Two layers:

* static assertions (always run): packaged tree layout, the substituted entry
  script (no leftover @pkgdatadir@ / @PACKAGE_VERSION@ markers; the baked
  pkgdatadir points inside the package and exists), python package and
  templates present, man page present; when the host has python3, an
  ast.parse syntax check of the entry + package modules; when it also has
  PyYAML, a parse check of every packaged YAML (templates + examples).
* runtime assertions (only when the host can actually run the tool, i.e.
  python3 + PyYAML importable):
    - `jigsaw-generate -v` reports version 0.2.7
    - `--help` prints the usage (puzzlefile[.yaml])
    - a real generation run over a shipped example puzzle with --nomakepdf
      (upstream gates the whole .tex pipeline on the makepdf option, so no
      LaTeX is invoked) exits 0 and produces .md output
    - a second run with the default (makepdf) options but a stub pdflatex on
      PATH proves the tex pipeline (table/puzzle .tex writing + the pdflatex
      invocation) works end to end.
    - the last two runtime items are the HarmonyOS-specific consumer use
      cases (end-to-end): a real generation over a shipped example puzzle
      plus the full makepdf pipeline, i.e. a complete consumer workflow
      satisfying pc-pr-review rule12 (not a bare assertion).

On a host without python3/PyYAML (e.g. the aarch64/OHOS CI worker) the
runtime layer is reported as deferred explicitly; static assertions still
apply.
"""
import os
import shutil

from conan import ConanFile


class JigsawGeneratorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The OHOS worker's /system/bin/sh (mksh) cannot exec the script via
        # its shebang path; resolve a bash explicitly (worker path as
        # fallback), same pattern as the procdump test.
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        # --auto: test.sh always runs the static layer and runs the runtime
        # layer only when python3+yaml are importable on the host.
        self.run(f"{bash} test.sh --auto", env="conanrun")
