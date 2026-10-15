#!/usr/bin/env python3
"""Conan test_package for kapptemplate 26.04.0 (consumer-side validation).

The packaged application ships a non-interactive command-line mode
(main.cpp): with six positional arguments it drives the real template
generator synchronously and returns, without loading the QML GUI:

    kapptemplate <name> <location> <author> <e-mail> <version> <template>

This consumer test executes that real code path and asserts on the produced
side effects (the generated project tree and its macro-expanded content),
not merely on the exit code:

  1. ``--version``           -> the KAboutData version is printed (QApplication
                                and the whole Qt6/KF6 link closure are loaded).
  2. ``--list-templates``    -> the installed template archives are enumerated
                                through QStandardPaths (kde-frameworks6,
                                kde-frameworks6-simple).
  3. generation              -> ``kde-frameworks6`` is unpacked into $TMPDIR and
                                the result is inspected: the project directory
                                and files exist with %{APPNAMELC}-expanded file
                                names, and the root CMakeLists.txt carries the
                                macro-expanded project() line.

Runtime-linking note (E537): the published KF6 libraries record
  * build-tree-relative DT_NEEDED entries ("../../bin/libKF6ConfigCore.so"),
    resolved by the OHOS loader against the process CWD, and
  * absolute DT_NEEDED entries recorded from a different builder's conan home
    ($HOME/.cache/conan2/p/<pkg>/lib/...), which do not exist here.
The farm + absolute-path materialization below mirror/repair both so the real
application can be executed (accessibility 26.04.3 / alligator 26.04.0
precedent). Writable HOME/XDG dirs are provided and every temp file goes under
the build folder (the device /tmp is read-only).
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class KAppTemplateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    # ── runtime linker repairs (E537) ──────────────────────────────────────

    def _find_readelf(self):
        for cand in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/storage/Users/currentUser/.harmonybrew/bin/readelf",
            "/usr/bin/readelf",
            "/bin/readelf",
        ):
            exe = shutil.which(cand) or cand
            try:
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _link_farm(self):
        # Relative DT_NEEDED entries ("../../bin/libKF6ConfigCore.so") resolve
        # against the process CWD. The consumer runs with CWD set to
        # <build>/consumer/run, so "../../bin" must land on a farm of every
        # dependency shared library and "../bin" on a shim pointing at it.
        # Everything is created *inside* the (git-ignored) conan build folder so
        # the recipe source tree is never polluted.
        farm = os.path.join(self.build_folder, "bin")
        os.makedirs(farm, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for layout in ("lib", "bin"):
                src = os.path.join(dep.package_folder, layout)
                if not os.path.isdir(src):
                    continue
                for name in os.listdir(src):
                    if ".so" not in name:
                        continue
                    link = os.path.join(farm, name)
                    if not os.path.lexists(link):
                        try:
                            os.symlink(os.path.join(src, name), link)
                        except OSError as exc:
                            self.output.warning(f"farm skip {name}: {exc}")
        up_bin = os.path.join(self.build_folder, "consumer", "bin")
        os.makedirs(os.path.dirname(up_bin), exist_ok=True)
        if not os.path.lexists(up_bin):
            try:
                os.symlink("../../bin", up_bin)
            except OSError as exc:
                self.output.warning(f"consumer/bin symlink fail: {exc}")
        return farm

    def _materialize_abs_deps(self):
        # Absolute-path DT_NEEDED entries recorded from another builder's conan
        # home: symlink every missing absolute path to the real library in the
        # matching dependency package.
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning("readelf not found; absolute DT_NEEDED materialization skipped")
            return
        seen = set()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if ".so" not in name or name in seen:
                    continue
                seen.add(name)
                lib_path = os.path.join(libdir, name)
                try:
                    rd = subprocess.run(
                        [readelf, "-d", lib_path], capture_output=True, text=True, timeout=60
                    ).stdout
                except OSError:
                    continue
                for m in re.finditer(r"Shared library: \[(/[^]]+\.so[^]]*)\]", rd):
                    abs_path = m.group(1)
                    if os.path.exists(abs_path):
                        continue
                    fname = os.path.basename(abs_path)
                    for d2 in self.dependencies.values():
                        if not d2.package_folder:
                            continue
                        cand = os.path.join(d2.package_folder, "lib", fname)
                        if os.path.exists(cand):
                            try:
                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                if not os.path.lexists(abs_path):
                                    os.symlink(cand, abs_path)
                            except OSError as exc:
                                self.output.warning(f"abs DT_NEEDED symlink fail {abs_path}: {exc}")
                            break

    # ── environment ────────────────────────────────────────────────────────

    def _consumer_env(self, dep, farm_bin):
        env = Environment()
        for p in self.dependencies.values():
            if p and p.package_folder:
                for layout in ("lib", "bin"):
                    d = os.path.join(p.package_folder, layout)
                    if os.path.isdir(d):
                        env.prepend_path("LD_LIBRARY_PATH", d)
                for plugins in (os.path.join(p.package_folder, "plugins"),
                                os.path.join(p.package_folder, "lib", "plugins")):
                    if os.path.isdir(plugins):
                        env.prepend_path("QT_PLUGIN_PATH", plugins)
                for qml in ("qml", os.path.join("lib", "qml")):
                    qml_dir = os.path.join(p.package_folder, qml)
                    if os.path.isdir(qml_dir):
                        env.prepend_path("QML2_IMPORT_PATH", qml_dir)
        env.prepend_path("LD_LIBRARY_PATH", farm_bin)
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)

        # Templates live under <pkg>/share/kdevappwizard/templates and are
        # located through QStandardPaths::GenericDataLocation (XDG_DATA_DIRS).
        env.define("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
        env.define("QT_QPA_PLATFORM", "offscreen")

        home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        tmpdir = os.path.join(self.build_folder, "test-tmp")
        for d, mode in ((home, 0o755), (xdg_runtime, 0o700), (tmpdir, 0o755)):
            os.makedirs(d, exist_ok=True)
            os.chmod(d, mode)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        env.define("TMPDIR", tmpdir)
        return env

    def _run(self, argv, cwd):
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=180, cwd=cwd)
        self.output.info(
            "$ {}\n  rc={}\n  stdout: {}\n  stderr: {}".format(
                " ".join(argv), proc.returncode, proc.stdout.strip(), proc.stderr.strip()
            )
        )
        return proc

    def test(self):
        dep = self.dependencies.get("kapptemplate")
        assert dep is not None and dep.package_folder is not None, (
            "kapptemplate not found in the dependency graph"
        )
        app_bin = os.path.join(dep.package_folder, "bin", "kapptemplate")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"

        farm_bin = self._link_farm()
        self._materialize_abs_deps()

        work = os.path.join(self.build_folder, "consumer")
        os.makedirs(work, exist_ok=True)
        # Run with CWD = <build>/consumer/run so that the "../../bin/..." and
        # "../bin/..." DT_NEEDED entries land on the farm created above.
        cwd = os.path.join(work, "run")
        os.makedirs(cwd, exist_ok=True)

        with self._consumer_env(dep, farm_bin).vars(self).apply():
            # 1. --version: KAboutData / QCommandLineParser + full link closure.
            v = self._run([app_bin, "--version"], cwd)
            assert v.returncode == 0, f"kapptemplate --version failed (rc={v.returncode}): {v.stderr}"
            vtext = v.stdout + v.stderr
            # Device-verified upstream version string: KAPPTEMPLATE_VERSION =
            # "0.1" + RELEASE_SERVICE_COMPACT_VERSION (26+04+0 = "26040") for
            # release-service 26.04.0. (The handoff's "0.1.260400" had an extra
            # trailing zero; the real binary prints "kapptemplate 0.1.26040".)
            assert "0.1.26040" in vtext, f"unexpected --version output: {vtext!r}"

            # 2. --list-templates: enumerate installed template archives.
            lt = self._run([app_bin, "--list-templates"], cwd)
            assert lt.returncode == 0, f"--list-templates failed (rc={lt.returncode}): {lt.stderr}"
            templates = lt.stdout.split()
            assert "kde-frameworks6" in templates, f"templates: {templates!r}"
            assert "kde-frameworks6-simple" in templates, f"templates: {templates!r}"

            # 3. generate a real project and inspect the output tree. The
            # generation runs through self.run so the conan harness asserts the
            # real exit code (a non-zero result fails the test package loudly).
            gen_root = os.path.join(work, "gen")
            os.makedirs(gen_root, exist_ok=True)
            self.run(
                '"{}" MyTestApp "{}" "Test Author" "test@example.org" "1.2.3" kde-frameworks6'.format(
                    app_bin, gen_root
                ),
                cwd=cwd,
            )

            # Generator creates <location>/<name.lower()> (generator.cpp).
            dest = os.path.join(gen_root, "mytestapp")
            assert os.path.isdir(dest), f"generated project dir missing: {dest}"

            # %{APPNAMELC} expansion in file names and the template layout.
            expected = [
                "CMakeLists.txt",
                "README",
                os.path.join("src", "CMakeLists.txt"),
                os.path.join("src", "main.cpp"),
                os.path.join("src", "mytestappwindow.cpp"),
                os.path.join("src", "mytestappview.cpp"),
            ]
            for rel in expected:
                full = os.path.join(dest, rel)
                assert os.path.exists(full), f"expected generated file missing: {rel}"

            # %{APPNAMELC}/%{VERSION} expansion in file *content*.
            cmake = os.path.join(dest, "CMakeLists.txt")
            with open(cmake, "r", errors="replace") as fh:
                body = fh.read()
            assert "project(mytestapp VERSION 1.2.3)" in body, (
                "macro expansion in generated CMakeLists.txt failed; got: " + body[:400]
            )
            self.output.info(f"kapptemplate consumer test: generated {dest} OK")
