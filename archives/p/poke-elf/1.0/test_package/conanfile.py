import json
import os

from conan import ConanFile
from conan.tools.env import Environment


class PokeElfTestConan(ConanFile):
    """test_package for poke-elf 1.0 -- consumer verification.

    Exercises the installed pickles for real through the poke binary:
    version, loading the elf pickle, ELF file-type/class constants and
    the AArch64 machine constant. All checks run via test.sh so the
    counts are deterministic (5 consumer checks).

    The elf pickles live outside poke's prefix, so they are exposed via
    POKE_LOAD_PATH (prepended to poke's load_path at startup; poke-elf
    manual "Installation"). poke's `-L FILE` is NOT a load-path option
    (it compiles FILE as a script and exits), so test.sh never passes
    -L and instead relies on POKE_LOAD_PATH + `load elf;`.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        poke_elf = self.dependencies[self.tested_reference_str.split("/")[0]]
        elf_pickles = os.path.join(poke_elf.package_folder, "share", "poke", "pickles")
        poke = self.dependencies["poke"]
        poke_data = os.path.join(poke.package_folder, "share", "poke")
        env = Environment()
        env.define("POKE_ELF_PICKLESDIR", elf_pickles)
        # Documented discovery mechanism for out-of-prefix pickles.
        env.define("POKE_LOAD_PATH", elf_pickles)
        env.define("POKEDATADIR", poke_data)
        env.define("POKECONFIGDIR", poke_data)
        env.define("POKEPICKLESDIR", os.path.join(poke_data, "pickles"))
        bash = None
        for cand in (os.environ.get("SHELL"), os.environ.get("CONFIG_SHELL"),
                     "/bin/sh", "/system/bin/sh",
                     "/data/service/hnp/bin/bash"):
            if cand and os.path.exists(cand):
                bash = cand
                break
        if bash is None:
            bash = "sh"
        command = "{} test.sh".format(bash)
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 5, "passedCount": 0}
        try:
            with env.vars(self, scope="run").apply():
                self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = 5
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
