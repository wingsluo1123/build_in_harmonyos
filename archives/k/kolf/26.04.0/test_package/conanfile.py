#!/usr/bin/env python3
"""Conan test_package for kolf 26.04.0 (application package).

kolf is a GUI game (QApplication). Upstream registers no test suite
(N=0: no tests/, autotests/ or add_test() in the 26.04.0 tarball), so the
consumer verification is a runtime smoke of the shipped executable
(kfourinline 26.04.0 / ktuberling 26.04.0 pattern):

  1. the binary exists in the package bin/ directory and is executable
  2. kolf --version prints the 26.04.0 version string and exits 0
     (KAboutData::setupCommandLine wires --version before the GUI main
     window is created; QT_QPA_PLATFORM=offscreen keeps it headless-safe)
  3. kolf --help prints the command-line interface and exits 0
     (proves the Qt and KDE runtime link completed)
  4. kolf --license prints the GPL license text and exits 0
     (proves the KAboutData metadata is intact)

Runtime environment (ktuberling 26.04.0 / kgoldrunner 26.04.0 precedent):
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so") are resolved through compatibility symlinks
  - build-machine absolute DT_NEEDED entries get an absolute-NEEDED
    fallback layer: the missing paths are created as symlinks to the real
    libraries found in the dependency packages (the OHOS musl loader
    resolves path-style NEEDED entries literally, no LD_LIBRARY_PATH
    fallback)
  - /system/lib64 for the compatible libc++_shared.so
  - the OHOS binary signature is refreshed before execution (freshly built
    executables need a .codesign section to be executable)
The assertions live in test.sh (POSIX sh); each passing check prints one
deterministic `SMOKE-PASS <name>` line which is counted for the
HMBS_TEST_PACKAGE_RESULT marker (kyua precedent: single deterministic
source, no arithmetic fixups). The no_tests upstream marker is re-emitted
every round from the package res/upstream_test_result.json persisted by
build() (inspircd 4.7.0 precedent; falls back to the audited reason when
the file is absent).
"""
import json
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KolfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive runtime DT_NEEDED of libKDEGames6 and the KF6 closure
        # (those packages don't propagate a runenv into the consumer graph,
        # so they must be declared here for the LD_LIBRARY_PATH collection
        # - libkdegames test_package precedent). NOTE: kio is intentionally
        # absent -- kolf no longer links KF6KIOCore (patch 0002 ports
        # openUrl to QFile/QtNetwork), so kio must not be pulled back into
        # the graph here (its cross-generation package_id would force a
        # source rebuild that fails the sandbox compiler check).
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kauth/6.18.0")
        self.requires("kbookmarks/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        # Round-18: kcrash/ktextwidgets ported away (patch 0003, no
        # published 6.18.0 OHOS binaries); kolf no longer links them so
        # the test graph must not pull them back (would force the same
        # failing source rebuild seen in preflight).
        self.requires("kdbusaddons/6.18.0")
        self.requires("kdnssd/6.29.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0.1")
        self.requires("kitemviews/6.18.0")
        self.requires("kjobwidgets/6.18.0")
        self.requires("knewstuff/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kwindowsystem/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("solid/6.18.0")
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")

    def _libdirs(self):
        dirs = []
        seen = set()
        for dep in self.dependencies.values():
            if not (dep and dep.package_folder):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if libdir not in seen and os.path.isdir(libdir):
                seen.add(libdir)
                dirs.append(libdir)
        return dirs

    def _prepare_runtime_links(self):
        """Compatibility symlinks for relative DT_NEEDED entries baked into
        the published KF6 packages ("../../bin/libKF6*.so" relative to the
        process cwd — ktuberling 26.04.0 / kgoldrunner 26.04.0 precedent)."""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    compat_libs.setdefault(name, os.path.join(libdir, name))
        # the relative path is resolved from cwd (the test runs from the
        # build folder): provide <build>/../../bin and <build>/bin farms
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_absolute_needed(self):
        """The published KF6/KDEGames6 binaries carry build-machine
        absolute paths in DT_NEEDED. Create the missing paths as symlinks
        to the real libraries found in the dependency packages
        (ktuberling 26.04.0 / kgoldrunner 26.04.0 precedent)."""
        import struct

        def elf_needed(path):
            """Minimal ELF DT_NEEDED extractor (no readelf dependency)."""
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF" or data[4] != 2:
                return []
            is_le = data[5] == 1
            e_shoff = struct.unpack_from("<Q" if is_le else ">Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3A)[0]
            e_shnum = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3C)[0]
            needed = []
            dynstr = None
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                if off + e_shentsize > len(data):
                    break
                sh_type = struct.unpack_from(
                    "<I" if is_le else ">I", data, off + 4)[0]
                if sh_type == 3:  # SHT_STRTAB
                    dynstr = off
                elif sh_type == 6:  # SHT_DYNAMIC
                    d_off = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, off + 0x18)[0]
                    d_size = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, off + 0x20)[0]
                    if dynstr is None:
                        continue
                    str_off = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, dynstr + 0x18)[0]
                    p = d_off
                    end = d_off + d_size
                    while p + 16 <= end and p + 16 <= len(data):
                        tag, val = struct.unpack_from(
                            "<QQ" if is_le else ">QQ", data, p)
                        if tag == 0:
                            break
                        if tag == 1:  # DT_NEEDED
                            s = str_off + val
                            e = data.index(b"\x00", s)
                            needed.append(data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

        # index: soname -> real file, from every dependency package libdir
        index = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        fixes = 0
        # scan every dependency libdir AND the tested package's own bin/
        # executable (its DT_NEEDED also carry build-machine absolute
        # paths: the linking machine resolved the KF6 deps into its own
        # cache layout).
        scan_roots = list(self._libdirs())
        pkg = self.dependencies.get("kolf")
        pkg_bin = None
        if pkg and pkg.package_folder:
            pkg_bin = os.path.join(pkg.package_folder, "bin")
            if os.path.isdir(pkg_bin):
                scan_roots.append(pkg_bin)
        for root in scan_roots:
            for name in os.listdir(root):
                full = os.path.join(root, name)
                if not os.path.isfile(full):
                    continue
                is_elfish = name.endswith(".so") or ".so." in name
                if root != pkg_bin and not is_elfish:
                    continue
                for entry in elf_needed(full):
                    if not entry.startswith("/"):
                        continue
                    if os.path.exists(entry):
                        continue
                    base = os.path.basename(entry)
                    source = index.get(base)
                    if not source:
                        continue
                    try:
                        os.makedirs(os.path.dirname(entry), exist_ok=True)
                        if not os.path.lexists(entry):
                            try:
                                os.symlink(source, entry)
                                fixes += 1
                            except OSError:
                                shutil.copy2(source, entry)
                                fixes += 1
                    except OSError as e:
                        self.output.warning(
                            f"cannot create NEEDED fallback {entry}: {e}")
        if fixes:
            self.output.info(
                "created %d absolute-NEEDED compatibility links" % fixes)

    def _resolve_host_tool(self, name):
        import glob as _glob
        cands = []
        try:
            _w = shutil.which(name)
            if _w:
                cands.append(_w)
        except Exception:
            pass
        cands.append("/data/service/hnp/bin/%s" % name)
        try:
            cands.append(os.path.join(os.path.expanduser("~"),
                                       ".harmonybrew", "bin", name))
        except Exception:
            pass
        for _pat in ("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/%s" % name,
                     "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/%s" % name):
            try:
                cands.extend(sorted(_glob.glob(_pat)))
            except Exception:
                pass
        seen = set()
        for _c in cands:
            if _c and _c not in seen:
                seen.add(_c)
                try:
                    if os.path.isfile(_c):
                        self.output.info("test host tool %s hit=%s" % (name, _c))
                        return _c
                    self.output.info("test host tool %s absent: %s" % (name, _c))
                except Exception:
                    continue
        self.output.warning("test host tool %s not found (tried %s)" % (name, cands))
        return ""

    def _sign(self, path):
        import subprocess
        objcopy = self._resolve_host_tool("llvm-objcopy")
        signer = self._resolve_host_tool("binary-sign-tool")
        if not signer:
            raise ConanException(
                "binary-sign-tool not found on this worker; cannot "
                "self-sign the freshly built kolf executable")
        if objcopy:
            subprocess.run([objcopy, "--remove-section", ".codesign", path],
                           check=True)
        else:
            self.output.warning(
                "llvm-objcopy not found; signing without stripping stale "
                ".codesign section")
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["kolf"]
        gui = os.path.join(pkg.package_folder, "bin", "kolf")
        if not os.path.isfile(gui):
            raise ConanException(f"kolf binary not found: {gui}")

        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        if str(self.settings.os) == "OHOS":
            self._sign(gui)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        # Qt platform plugins (offscreen) live in the qtbase package
        # (plugins/platforms or lib/plugins/platforms).
        plugin_dirs = []
        platforms = []
        for p in self.dependencies.values():
            if p.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    d = os.path.join(p.package_folder, rel)
                    if os.path.isdir(d):
                        plugin_dirs.append(d)
                    pd = os.path.join(d, "platforms")
                    if os.path.isdir(pd):
                        platforms.append(pd)

        # QStandardPaths must find the game's own share/kolf tree
        # (courses/, sounds/, themes/) for startup asset lookup.
        data_dirs = []
        for dep in list(self.dependencies.values()):
            if dep and dep.package_folder:
                share = os.path.join(dep.package_folder, "share")
                if os.path.isdir(share):
                    data_dirs.append(share)

        env = Environment()
        env.append("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        for d in plugin_dirs:
            env.append("QT_PLUGIN_PATH", d)
        for d in platforms:
            env.append("QT_QPA_PLATFORM_PLUGIN_PATH", d)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                qml_dir = os.path.join(dep.package_folder, "qml")
                if os.path.isdir(qml_dir):
                    env.append("QML2_IMPORT_PATH", qml_dir)
        if data_dirs:
            env.append("XDG_DATA_DIRS", os.pathsep.join(data_dirs))
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)

        # conan's self.run() may spawn a fresh shell environment that
        # drops the appended loader vars; persist them via os.environ so
        # the subprocess inherits them (ktuberling 26.04.0 precedent,
        # belt-and-braces with env.vars above).
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(
                platforms
            )
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)
        if data_dirs:
            os.environ["XDG_DATA_DIRS"] = os.pathsep.join(data_dirs)

        # test.sh uses POSIX shell syntax (ktuberling pattern; avoids
        # binding to a bash install path on the target device). Each
        # passing check prints one deterministic `SMOKE-PASS <name>` line.
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        test_script = os.path.join(self.source_folder, "test.sh")
        with env.vars(self).apply():
            self.run(
                f'{shlex.quote(shell)} '
                f'{shlex.quote(test_script)} '
                f'{shlex.quote(gui)}',
                cwd=self.build_folder,
            )
        # Deterministic count source (kyua precedent): re-run the script
        # capturing stdout and count SMOKE-PASS lines; no string-count
        # arithmetic on the framework output, no returncode-based fixups.
        python = os.environ.get("HMBS_PYTHON3") or sys.executable or "python3"
        _ = python
        capture_env = dict(os.environ)
        proc = subprocess.run(
            [shell, test_script, gui],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            cwd=self.build_folder,
            env=capture_env,
        )
        self.output.info(proc.stdout[-3000:] if proc.stdout else "")
        ok_count = 0
        for line in (proc.stdout or "").splitlines():
            if line.startswith("SMOKE-PASS "):
                ok_count += 1
        discovered = 4
        tp_marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == discovered,
            "command": "sh test.sh <kolf-bin> (binary exists + --version + --help + --license)",
            "discovered": discovered,
            "passedCount": ok_count,
        }
        tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
        print(tp_msg, flush=True)
        self.output.info(tp_msg)
        if not tp_marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, discovered)
            )
        # Re-emit the upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json (runs every round, even on
        # cached build() which skips the main marker; kyua precedent).
        result_path = os.path.join(
            pkg.package_folder, "res", "upstream_test_result.json"
        )
        if os.path.isfile(result_path):
            with open(result_path, "r", encoding="utf-8") as handle:
                upstream = json.load(handle)
        else:
            self.output.warning(
                "upstream_test_result.json not found in package; "
                "emitting audited no_tests fallback"
            )
            upstream = {
                "status": "no_tests",
                "framework": "ctest",
                "command": "",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "Audited kolf-26.04.0.tar.xz: no tests/, autotests/ "
                          "or test/ directory; no enable_testing()/add_test()/ecm_add_test() "
                          "in any CMakeLists.txt; upstream QA via KDE CI only.",
            }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        self.output.info("kolf consumer smoke passed")
