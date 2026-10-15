#!/usr/bin/env python3
"""Test package — israel-rail-api 0.1.5 consumer smoke test.

R34: must really exercise the package under test — import israelrailapi
from the installed site-packages and call its public API surface offline
(no network: station lookup + API argument preparation).
"""
import os
import sys

from conan import ConanFile


class IsraelRailApiTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # requests 的传递依赖在 test 图中可能被 skip 不落盘，显式物化以供 import
        self.requires("chardet/5.2.0")
        self.requires("idna/3.18")
        self.requires("urllib3/2.7.0")

    def test(self):
        import glob
        sp, paths = [], []
        for dep in self.dependencies.host.values():
            hits = glob.glob(os.path.join(
                dep.package_folder, "**", "site-packages"), recursive=True)
            if dep.ref.name == "israel-rail-api":
                sp.extend(hits)
            else:
                paths.extend(hits)
        assert sp, "israel-rail-api site-packages not found in deps"
        code = (
            "import sys;"
            + "".join("sys.path.insert(0, '%s');" % p for p in sp + paths)
            + "from israelrailapi import train_station, api;"
            "assert str(680) == train_station.lookup_station('Jerusalem- yitzhak navon');"
            "assert str(7500) == train_station.lookup_station('Dimona');"
            "a = api.IsraelRailApi('MyApi', {'required': {}, 'default': {'default': 5}});"
            "assert a.url == api.API_BASE + '/MyApi';"
            "assert a.prepare_arguments({'required': 'Hello'}) == {'required': 'Hello', 'default': 5};"
            "print('test_package: israel-rail-api smoke OK')"
        )
        self.run('python3 -c "%s"' % code)
