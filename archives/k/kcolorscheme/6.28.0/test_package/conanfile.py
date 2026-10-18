#!/usr/bin/env python3
"""Conan test_package for kcolorscheme 6.28.0.

Consumer-side verification (R34: real API usage) of the exported
KF6ColorScheme CMake package:

  * find_package(KF6ColorScheme) resolves through the project-installed
    KF6ColorSchemeConfig.cmake -- the recipe sets cmake_find_mode=none so
    CMakeDeps does not shadow it.
  * test_kcolorscheme drives the public surface headless
    (QT_QPA_PLATFORM=offscreen): KColorScheme background/foreground/
    decoration lookups across all 7 ColorSets, the contrast/frameContrast
    accessors, the static and member shade() overloads,
    adjustBackground() palette rewrites and copy equality, plus the
    KStatefulBrush constructor overloads and the documented
    default-constructed null brush.
  * on OHOS, test_kcolorscheme_elf.py checks the installed shared object
    is a single unversioned AArch64 ELF64 (no SONAME symlink chain --
    OHOS /storage forbids symlinks) with
    DT_SONAME=libKF6ColorScheme.so, basename-only DT_NEEDED entries and
    the .codesign section.

The build/run environment mirrors krunner 6.28.0 (krunner 6.28.0 /
kscreenlocker 6.7.2 precedent): QT_QPA_PLATFORM=offscreen, the SDK
llvm/lib on LD_LIBRARY_PATH so CMake try-compiles can link, and every
dependency's lib dir on LD_LIBRARY_PATH at run time.
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KcolorschemeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        # Expose every contributor's cmake dir so the find_dependency()
        # chain in KF6ColorSchemeConfig.cmake resolves.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory, which CI workers may not export via
        # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link
        # (krunner 6.28.0 / kitemviews 6.26.0 / kscreenlocker 6.7.2
        # precedent). The SDK version stays unpinned on purpose: a pin
        # breaks as soon as an image ships a different SDK release. Must
        # not clobber the conanbuild env on other hosts.
        env = Environment()
        for sdk_llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        env.append(
            "QT_PLUGIN_PATH",
            [
                os.path.join(p.package_folder, "plugins")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        # The consumer test drives the public surface headless; the QPA
        # offscreen plugin comes from the qtbase package.
        env.define("QT_QPA_PLATFORM", "offscreen")
        # CI debuggability: ctest reports a failed test as a bare
        # "***Failed N sec" unless output-on-failure is requested, so a CI
        # failure would carry no cause at all. Export it so the failed
        # test's own output (loader diagnostics, Qt warnings, per-case
        # lines) reaches the log.
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")

        # Hermetic XDG roots: KColorScheme opens its KSharedConfig through
        # KConfig/QStandardPaths (scheme entries under XDG_CONFIG_HOME,
        # scheme files under the XDG data dirs); pinning all roots keeps
        # the run independent of whatever the worker has in ~/.config or
        # /run/user.
        home = os.path.join(self.build_folder, "ohos-xdg")
        for sub in ("config", "configdirs", "data", "datadirs", "runtime"):
            os.makedirs(os.path.join(home, sub), exist_ok=True)
        env.define("HOME", home)
        env.define("XDG_CONFIG_HOME", os.path.join(home, "config"))
        env.define("XDG_CONFIG_DIRS", os.path.join(home, "configdirs"))
        env.define("XDG_DATA_HOME", os.path.join(home, "data"))
        env.define("XDG_DATA_DIRS", os.path.join(home, "datadirs"))
        env.define("XDG_RUNTIME_DIR", os.path.join(home, "runtime"))

        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_kcolorscheme"
        )

        run_cwd = None
        with env.vars(self).apply():
            # OHOS-specific: the installed shared object must be a single
            # unversioned AArch64 ELF64 (no SONAME symlink chain) with
            # DT_SONAME=libKF6ColorScheme.so, basename-only DT_NEEDED and
            # the .codesign section.
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                # E537: several published KF6 libraries carry
                # build-tree-relative DT_NEEDED entries
                # (../../bin/libKF6*.so) that the OHOS loader resolves
                # against the process CWD. Stage a compatibility bin
                # directory the way the kconfig recipe stages one for its
                # own ctest (_prepare_ctest_runtime_links): the test
                # processes run with CWD = build_folder, two levels below
                # the test_package root, so <recipe_folder>/bin is the
                # ../../bin/ target. Every transitive dependency's
                # libKF6*.so is copied there (unversioned basenames, the
                # names the relative entries reference). Copies, not
                # symlinks -- OHOS /storage forbids symlinks.
                compat_bin = os.path.join(self.recipe_folder, "bin")
                os.makedirs(compat_bin, exist_ok=True)
                wanted = set()
                for _pkg in self._iter_transitive_pkgs():
                    _libdir = os.path.join(_pkg.package_folder, "lib")
                    if not os.path.isdir(_libdir):
                        continue
                    for _name in os.listdir(_libdir):
                        if not (_name.startswith("libKF6")
                                and _name.endswith(".so")):
                            continue
                        _src = os.path.join(_libdir, _name)
                        _dst = os.path.join(compat_bin, _name)
                        if os.path.isfile(_src):
                            wanted.add(_name)
                            # Refresh unconditionally: a copy left over
                            # from an earlier conan create in this recipe
                            # dir may no longer match the rebuilt
                            # dependency graph, and the consumer run would
                            # silently load the stale library.
                            shutil.copy2(_src, _dst)
                # Drop leftovers the refresh above can never remove: a
                # stale libKF6*.so whose library left the dependency
                # graph would still sit in ../../bin for the loader to
                # pick up. Removed before the fixdeps scan so its
                # basename map only sees the current graph.
                for _name in sorted(os.listdir(compat_bin)):
                    if not (_name.startswith("libKF6")
                            and _name.endswith(".so")):
                        continue
                    if _name not in wanted:
                        _stale = os.path.join(compat_bin, _name)
                        if os.path.isfile(_stale):
                            os.remove(_stale)
                # Registry hygiene, absolute variant: several published KF6
                # libraries also carry machine-private absolute DT_NEEDED
                # paths into the publisher's Conan home build folders (e.g.
                # <HOME>/.cache/conan2/p/b/kconf<hash>/p/lib/libKF6ConfigWidgets.so).
                # An absolute entry is opened literally by the loader -- no
                # search path applies -- so on any worker without that
                # folder the process dies at load time, before main(), with
                # "cannot open shared object file" (manifesting as a bare
                # 0.35 s ctest death). Materialize every missing
                # path-carrying entry at its literal path from the runtime
                # library set (helper script; copies, not symlinks).
                fixdeps = os.path.join(
                    self.recipe_folder, "test_kcolorscheme_fixdeps.py"
                )
                interpreter = sys.executable or "python3"
                self.run(
                    " ".join(
                        shlex.quote(x)
                        for x in (interpreter, fixdeps, compat_bin)
                    ),
                    env="conanrun",
                )
                run_cwd = self.build_folder

                package_folder = self.dependencies[
                    self.tested_reference_str
                ].package_folder
                script = os.path.join(
                    self.recipe_folder, "test_kcolorscheme_elf.py"
                )
                self.run(
                    " ".join(
                        shlex.quote(x)
                        for x in (interpreter, script, package_folder)
                    ),
                    env="conanrun",
                )

            # Run the consumer test directly first: its stdout/stderr (the
            # per-case TEST PASS/FAIL lines, loader diagnostics, Qt
            # warnings) must reach the CI log even when a ctest failure
            # would otherwise abort test() before the direct run. ctest
            # stays the acceptance gate right after; either failure still
            # throws and the package still goes red.
            self.run(shlex.quote(executable), env="conanrun", cwd=run_cwd)
            cmake = CMake(self)
            cmake.test()

    def _iter_transitive_pkgs(self):
        """Yield every package below the tested one, once each."""
        stack = [self.dependencies.get(self.tested_reference_str)]
        seen = set()
        while stack:
            node = stack.pop()
            sub = getattr(node, "dependencies", None)
            if not sub:
                continue
            for _req, dep in sub.items():
                if id(dep) in seen or not dep.package_folder:
                    continue
                seen.add(id(dep))
                yield dep
                stack.append(dep)
