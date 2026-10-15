#!/usr/bin/env python3
"""Conan test_package for kwrited 6.7.2 (OHOS).

The delivered product is bin/kwrited, built through upstream's
BUILD_AS_EXECUTABLE branch (forced by KPty_HAVE_UTEMPTER=FALSE in the packaged
kpty/6.26.0). The daemon takes no command line options and reports nothing on
stdout, so the consumer test is a real execution test (R34):

  1. the packaged bin/kwrited exists, is executable and carries the
     notification/autostart files upstream installs;
  2. starting it under the offscreen QPA platform loads the whole Qt6/KF6 link
     closure and allocates the pty: the process must still be alive after the
     grace period;
  3. its stdin must be a pty slave -- the executable branch dup2()s
     pty->slaveFd() to fd 0, so /proc/<pid>/fd/0 resolves to /dev/pts/N;
  4. SIGTERM drives the graceful path (~KWrited calls pty->logout()).

The assertions live in test_app.sh so the same check can be reproduced by hand
on a device; this recipe assembles the runtime environment (dependency libs,
offscreen QPA, private HOME/XDG_RUNTIME_DIR) and runs it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment


class KWritedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KF6 Pty is the runtime prerequisite that defines the delivered
        # flavour; declare it explicitly so the test resolves the same closure.
        self.requires("kpty/6.26.0")

    def layout(self):
        cmake_layout(self)

    def test(self):
        dep = self.dependencies.get("kwrited")
        assert dep is not None and dep.package_folder, (
            "kwrited is not present in the dependency graph"
        )
        pkg_bin = os.path.join(dep.package_folder, "bin", "kwrited")
        assert os.path.exists(pkg_bin), (
            "missing packaged executable: {}".format(pkg_bin)
        )
        assert os.access(pkg_bin, os.X_OK), (
            "packaged executable is not executable: {}".format(pkg_bin)
        )

        # Upstream installs kwrited.notifyrc for both branches and
        # kwrited-autostart.desktop only for the executable branch; their
        # presence proves the delivered artefact is the executable flavour.
        notifyrc = os.path.join(
            dep.package_folder, "share", "knotifications6", "kwrited.notifyrc"
        )
        assert os.path.exists(notifyrc), (
            "missing installed notifyrc: {}".format(notifyrc)
        )
        autostart = os.path.join(
            dep.package_folder, "etc", "xdg", "autostart", "kwrited-autostart.desktop"
        )
        assert os.path.exists(autostart), (
            "missing autostart entry (executable branch not built?): {}".format(
                autostart
            )
        )

        script = os.path.join(self.source_folder, "test_app.sh")
        assert os.path.exists(script), "missing consumer test script: {}".format(script)

        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
        home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        env.define("CONSUMER_TEST_TMP", self.build_folder)
        for item in self.dependencies.values():
            if item and item.package_folder:
                lib_dir = os.path.join(item.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins_dir = os.path.join(item.package_folder, "plugins")
                if os.path.isdir(plugins_dir):
                    env.prepend_path("QT_PLUGIN_PATH", plugins_dir)

        with env.vars(self).apply():
            # R34: real execution of the packaged binary.
            self.run('sh "{}" "{}" {}'.format(script, pkg_bin, 5), env="conanrun")
