#!/usr/bin/env python3
"""Conan test_package for byobu — verifies the installed scripts work."""
import os
from conan import ConanFile

class ByobuTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["byobu"]
        byobu_prefix = dep.package_folder
        bin_dir = dep.cpp_info.bindirs[0]
        byobu_bin = os.path.join(bin_dir, "byobu")
        self.run("test -f '%s'" % byobu_bin, env="conanrun")
        self.run("test -x '%s'" % byobu_bin, env="conanrun")
        self.run("head -1 '%s' | grep -q '^#!.*sh'" % byobu_bin, env="conanrun")
        self.run("grep -q 'version' '%s'" % byobu_bin, env="conanrun")
        col1_bin = os.path.join(bin_dir, "col1")
        self.run("test -x '%s'" % col1_bin, env="conanrun")
        self.run("'%s' --version" % col1_bin, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/dirs'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/common'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/colors'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/constants'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/share/byobu/status/status'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/share/byobu/status/statusrc'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/etc/byobu/backend'" % byobu_prefix, env="conanrun")
        self.run("test -L '%s/bin/byobu-screen'" % byobu_prefix, env="conanrun")
        self.run("test -L '%s/bin/byobu-tmux'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/share/man/man1/byobu.1'" % byobu_prefix, env="conanrun")
        self.run("test -n '$BYOBU_PREFIX'", env="conanrun")
