#!/usr/bin/env python3
"""Check the two installed Pathrate programs on a HarmonyOS PC."""

from conan import ConanFile


class PathrateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.py", "pace_udp.c", "ohos_consumer.c", "run_consumer.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f"{cc} -shared -fPIC pace_udp.c -o pace_udp.so -ldl")
        self.run(f"{cc} -std=c11 -Wall -Wextra ohos_consumer.c -o ohos_consumer")

    def test(self):
        self.run("python3 test.py", env="conanrun")
        self.run("python3 run_consumer.py", env="conanrun")
