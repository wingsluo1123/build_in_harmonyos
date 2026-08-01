#!/usr/bin/env python3
"""Conan test_package for wdq2wav."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Wdq2wavTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        output_path = os.path.join(self.build_folder, "wdq2wav-help.txt")
        self.run(f"wdq2wav -h > {output_path}", env="conanrun")
        with open(output_path, "r", encoding="utf-8") as help_file:
            help_text = help_file.read()
        if "usage:" not in help_text or "WinDAQ" not in help_text or "wav-file" not in help_text:
            raise Exception("wdq2wav help output did not contain expected usage text")
