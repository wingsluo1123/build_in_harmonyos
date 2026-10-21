#!/usr/bin/env python3
"""Conan test_package — skiboot 7.0 OPAL userspace utilities on OHOS/aarch64."""
import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class SkibootTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["skiboot"].package_folder
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ohos.py")
        self.run(f'"{sys.executable}" "{script}" "{pkg}"')

        upstream = os.path.join(pkg, "res", "hmbs_upstream.json")
        if not os.path.isfile(upstream):
            raise ConanException("res/hmbs_upstream.json missing from package")
        with open(upstream, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
