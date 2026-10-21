#!/usr/bin/env python3
"""Conan test_package — pipewire 1.6.9 L1 test."""
import os
import shlex
import shutil
import socket
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


def find_bindable_runtime_dir():
    """Return a directory that accepts an AF_UNIX bind, or None.

    The default home directory lives on HMDFS, which rejects bind() with
    EPERM, so the daemon end-to-end case probes a few candidates and lets
    test_ohos skip only when none of them is usable.
    """
    candidates = [
        os.environ.get("PIPEWIRE_E2E_TMP"),
        "/data/storage/el2/base",
        os.path.join(os.environ.get("HOME", "."), "tmp"),
        "/tmp",
        "/dev/shm",
    ]
    seen = set()
    for d in candidates:
        if not d or d in seen or not os.path.isdir(d):
            continue
        seen.add(d)
        probe = None
        try:
            # mkdtemp() creates a fresh private directory; a predictable
            # pid-based path could be pre-created by another user in the
            # shared writable directories (/tmp, /dev/shm).
            probe = tempfile.mkdtemp(prefix="pw-e2e-probe-", dir=d)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                s.bind(os.path.join(probe, "sock"))
            finally:
                s.close()
            return d
        except OSError:
            continue
        finally:
            # probe stays None when mkdtemp() itself failed; the finally
            # block runs before `continue` takes effect.
            if probe is not None:
                shutil.rmtree(probe, ignore_errors=True)
    return None


class PipewireTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        lib_dirs = []
        spa_plugin_dir = None
        module_dir = None
        pkg_bin_dir = None
        pkg_conf_dir = None
        for _name, dep in self.dependencies.items():
            if getattr(dep.cpp_info, "libdirs", None):
                for d in dep.cpp_info.libdirs:
                    p = os.path.join(dep.package_folder, d)
                    lib_dirs.append(p)
                    cand = os.path.join(p, "spa-0.2")
                    if os.path.isdir(cand):
                        spa_plugin_dir = cand
                    cand = os.path.join(p, "pipewire-0.3")
                    if os.path.isdir(cand):
                        module_dir = cand
            # Always pass the dependency bin directory, even when it does not
            # exist: test_ohos distinguishes "package lost its bin/ tree" (a
            # hard failure) from "no AF_UNIX-bindable runtime dir" (SKIP).
            pkg_bin_dir = os.path.join(dep.package_folder, "bin")
            cand = os.path.join(dep.package_folder, "share", "pipewire")
            if os.path.isdir(cand):
                pkg_conf_dir = cand
        env = Environment()
        if lib_dirs:
            env.define("LD_LIBRARY_PATH", os.pathsep.join(lib_dirs))
        if spa_plugin_dir:
            env.define("SPA_PLUGIN_DIR", spa_plugin_dir)
        if module_dir:
            env.define("PIPEWIRE_MODULE_DIR", module_dir)
        if pkg_bin_dir:
            env.define("PIPEWIRE_BIN_DIR", pkg_bin_dir)
        if pkg_conf_dir:
            env.define("PIPEWIRE_CONFIG_DIR", pkg_conf_dir)
        e2e_tmp = find_bindable_runtime_dir()
        if e2e_tmp:
            env.define("PIPEWIRE_E2E_TMP", e2e_tmp)
        bindir = self.cpp.build.bindirs[0]
        with env.vars(self).apply():
            for exe in ("test_pipewire", "test_ohos"):
                test_bin = os.path.join(bindir, exe)
                self.run(shlex.quote(test_bin))