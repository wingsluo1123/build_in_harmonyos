#!/usr/bin/env python3
"""Conan test_package — cosmic-icon 1.4.0"""
from conan import ConanFile
import os


class CosmicIconTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        icon_dir = os.path.join(self.dependencies["cosmic-icon"].package_folder,
                                "share", "icons", "Cosmic")
        if not os.path.isdir(icon_dir):
            raise Exception(f"Icon directory not found: {icon_dir}")

        # 递归扫描图标文件
        svg_count = 0
        for root, dirs, files in os.walk(icon_dir):
            for f in files:
                if f.endswith(".svg"):
                    path = os.path.join(root, f)
                    size = os.path.getsize(path)
                    if size < 100:
                        raise Exception(f"SVG file too small (empty?): {path} ({size} bytes)")
                    svg_count += 1

        if svg_count == 0:
            raise Exception("No SVG icon files found under install dir")

        print(f"cosmic-icon: {svg_count} SVG files installed OK")
