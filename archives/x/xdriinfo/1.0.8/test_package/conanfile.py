#!/usr/bin/env python3
"""Conan test_package — xdriinfo 1.0.8.

xdriinfo is a command line tool, so the consumer test really executes the
packaged binary (R34). xdriinfo.c resolves two DRI-config entry points via
glXGetProcAddressARB *before* it parses argv; with mesa's libGL both resolve to
non-NULL even without an X server, so the display-independent command line
paths are reachable and are asserted on real output:

  * `xdriinfo --version` / `-version`  -> stdout contains "xdriinfo 1.0.8"
  * `xdriinfo -help`                   -> usage banner, exit 0
  * `xdriinfo -Zz` (unknown option)    -> usage + non-zero exit
  * `xdriinfo nscreens` (no display)   -> non-zero exit + "Couldn't open display"

The last one exercises the real XOpenDisplay failure path on a headless
device; DISPLAY is cleared so the result is deterministic.

Runtime library resolution: libGL.so.1 pulls in libgallium-24.3.4.so (and
through it libLLVM.so.20.1), plus the libxcb extension libraries and expat.
The conanrun environment covers the conan graph; the OHOS SDK directories are
added for the toolchain-provided libc++_shared.so and libz.so that are not
part of the graph.
"""
import glob
import os
import shlex

from conan import ConanFile


class XdriinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _graph_lib_dirs(self):
        """lib/ directories of every host dependency in the graph."""
        dirs = []
        for dep in self.dependencies.host.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                dirs.append(lib_dir)
        return dirs

    def _sdk_runtime_dirs(self):
        """OHOS SDK directories shipping libc++_shared.so / libz.so."""
        if str(self.settings.os) != "OHOS":
            return []
        sdk_roots = ["/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"]
        sdk_roots.extend(sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*")))
        result = []
        for sdk_root in sdk_roots:
            native = os.path.join(sdk_root, "ohos", "native")
            candidates = [
                os.path.join(native, "llvm", "lib", "aarch64-linux-ohos", "c++"),
                os.path.join(native, "llvm", "lib", "aarch64-linux-ohos"),
                os.path.join(native, "sysroot", "usr", "lib", "aarch64-linux-ohos"),
            ]
            for candidate in candidates:
                if not os.path.isdir(candidate):
                    continue
                if (os.path.isfile(os.path.join(candidate, "libc++_shared.so"))
                        or os.path.isfile(os.path.join(candidate, "libz.so"))):
                    result.append(candidate)
            if result:
                break
        return list(dict.fromkeys(result))

    def _runtime_dirs(self):
        return list(dict.fromkeys(self._graph_lib_dirs() + self._sdk_runtime_dirs()))

    def test(self):
        binary = os.path.join(self.dependencies["xdriinfo"].package_folder,
                              "bin", "xdriinfo")
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xdriinfo.sh")
        runtime_dirs = self._runtime_dirs()
        self.output.info("runtime LD_LIBRARY_PATH=%s" % ":".join(runtime_dirs))
        command = " ".join([
            shlex.quote(shell),
            shlex.quote(script),
            shlex.quote(binary),
            shlex.quote(":".join(runtime_dirs)),
        ])
        self.run(command, env="conanrun")
