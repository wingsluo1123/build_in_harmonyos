import os
import shlex
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SgaConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        binary = os.path.join(self.dependencies["sga"].cpp_info.bindirs[0], "sga")
        if not os.path.isfile(binary):
            raise RuntimeError("tested package's executable is absent")
        if can_run(self):
            self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "test_sga.py"),
                                 binary, os.path.join(self.build_folder, "consumer")]), env="conanrun")
