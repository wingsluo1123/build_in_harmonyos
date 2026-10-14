#!/usr/bin/env python3
"""Conan recipe — zfs-fuse 0.7.0 (SCons, application).

zfs-fuse is a user-space port of Solaris ZFS to FUSE/Linux. Upstream 0.7.0
ships a Python2 SCons build; the OHOS patch set modernizes it to Python3,
adds aarch64/musl compatibility shims and relocatable runtime paths, and
builds the full CLI toolset (zfs-fuse daemon, zfs, zpool, zdb, ztest,
zstreamdump).

build() also runs the upstream user-space test suite: `ztest` (in-kernel
API pool exerciser with SIGKILL crash tolerance) followed by the zdb
integrity verification ztest invokes. `zdb -l` label parsing is checked as
the nvlist/XDR shim smoke test.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZfsFuseConan(ConanFile):
    name = "zfs-fuse"
    version = "0.7.0"
    description = ("User-space port of Solaris ZFS to FUSE/Linux: zfs-fuse "
                   "daemon plus zfs/zpool/zdb/ztest/zstreamdump CLI tools.")
    license = "CDDL-1.0"
    homepage = "https://zfs-fuse.net/"
    url = "https://github.com/zfs-fuse/zfs-fuse"
    topics = ("zfs", "fuse", "filesystem", "storage")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # SCons 4.10.1 as an isolated pip install (serf/1.3.10 precedent).
    _SCONS_VERSION = "4.10.1"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zfs-fuse recipe is validated for Linux/OHOS, not %s"
                % self.settings.os)

    def requirements(self):
        # All published on the ohpcd remote (R36 checked by W0 preflight).
        self.requires("libfuse/2.9.9")
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # helpers (serf/1.3.10 precedents)
    # ------------------------------------------------------------------

    def _hmbs_tmpdir(self):
        # HarmonyOS PC has read-only /tmp; write-probe every candidate
        # (coinor-vol/1.5.4 lesson: isdir alone is not proof on HMDFS).
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            val = (os.environ.get(key, "") or "").strip()
            if not val:
                continue
            try:
                os.makedirs(val, exist_ok=True)
                probe = os.path.join(val, ".hmbs-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                try:
                    tempfile.tempdir = None
                except Exception:
                    pass
                return val
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, "_tmp")
        os.makedirs(fallback, exist_ok=True)
        try:
            probe = os.path.join(fallback, ".hmbs-write-probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.unlink(probe)
        except OSError as exc:
            raise ConanException(
                "no writable tmpdir (build fallback %s unusable: %r)"
                % (fallback, exc))
        try:
            tempfile.tempdir = None
        except Exception:
            pass
        return fallback

    def _tool(self, key, fallbacks):
        # R33: compilers come from Conan conf, never from bare shell env.
        try:
            execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except ConanException:
            execs = {}
        configured = (execs.get(key) if execs else None) or None
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        if configured:
            self.output.warning(
                "tools.build:compiler_executables[%s]=%s not usable; "
                "falling back to PATH lookup" % (key, configured))
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        return fallbacks[0]

    def _ar_ranlib(self, cc):
        # Resolve explicit AR/RANLIB: env override first, then the CC
        # directory, then PATH (serf round-4: /system/bin/sh PATH lacks the
        # toolchain dir, so bare `ar` fails with Error 127).
        cc_dir = ""
        try:
            if cc and os.path.isabs(cc):
                cc_dir = os.path.dirname(cc)
        except Exception:
            pass

        def _probe(cand):
            return bool(cand and os.path.isfile(cand) and os.path.getsize(cand) > 0)

        ar = ""
        for key in ("AR", "HMBS_AR"):
            cand = (os.environ.get(key, "") or "").strip()
            if _probe(cand):
                ar = cand
                break
        if not ar:
            for name in ("llvm-ar", "aarch64-linux-ohos-ar", "ar"):
                if cc_dir and _probe(os.path.join(cc_dir, name)):
                    ar = os.path.join(cc_dir, name)
                    break
                found = shutil.which(name)
                if _probe(found):
                    ar = found
                    break
        ranlib = ""
        for key in ("RANLIB", "HMBS_RANLIB"):
            cand = (os.environ.get(key, "") or "").strip()
            if _probe(cand):
                ranlib = cand
                break
        if not ranlib:
            for name in ("llvm-ranlib", "aarch64-linux-ohos-ranlib", "ranlib"):
                if cc_dir and _probe(os.path.join(cc_dir, name)):
                    ranlib = os.path.join(cc_dir, name)
                    break
                found = shutil.which(name)
                if _probe(found):
                    ranlib = found
                    break
        if ar:
            self.output.info("usable AR: %s" % ar)
        if ranlib:
            self.output.info("usable RANLIB: %s" % ranlib)
        return ar, ranlib

    def _scons_env(self):
        env = dict(os.environ)
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        old = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = scons_prefix + (os.pathsep + old if old else "")
        tmpdir = self._hmbs_tmpdir()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        # Fork-pressure guard (libarchive-tools/3.8.8 precedent).
        env.setdefault("MAKEFLAGS", "-j1")
        # Toolchain: CC/AR/RANLIB are consumed by the patched SConstruct via
        # os.environ (upstream interface), values resolved from Conan conf.
        cc = self._tool("c", ("clang", "cc", "gcc"))
        env["CC"] = cc
        ar, ranlib = self._ar_ranlib(cc)
        if ar:
            env["AR"] = ar
        if ranlib:
            env["RANLIB"] = ranlib
        cc_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        if cc_dir and os.path.isdir(cc_dir):
            path = env.get("PATH", "")
            if cc_dir not in path.split(os.pathsep):
                env["PATH"] = cc_dir + (os.pathsep + path if path else "")
        # Dependency prefixes (patched SConstruct interface).
        env["OPENSSL_PREFIX"] = self.dependencies["openssl"].package_folder
        env["ZLIB_PREFIX"] = self.dependencies["zlib"].package_folder
        env["FUSE_PREFIX"] = self.dependencies["libfuse"].package_folder
        # Relocatable runtime dirs for the upstream test run (build tree).
        test_dir = os.path.join(self.build_folder, "zfs-run")
        env["ZFS_SOCK_DIR"] = test_dir
        env["ZPOOL_CACHE_DIR"] = test_dir
        env["ZFS_LOCK_DIR"] = test_dir
        return env

    def _install_scons(self):
        tmpdir = self._hmbs_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        cache_dir = os.path.join(tmpdir, "pip-cache")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = tmpdir
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)
        self.run(
            "python3 -m pip install --quiet --no-input "
            "--cache-dir=\"%s\" --target=\"%s\" scons==%s" % (
                cache_dir, scons_prefix, self._SCONS_VERSION),
            env="build",
        )
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
        except OSError:
            pass
        # OHOS has no /bin/sh: point the SCons POSIX platform at the system
        # shell (serf/1.3.10 + gpsd/3.26 precedent).
        self.run(
            "PYTHONPATH=\"%s\" python3 -c \""
            "import SCons.Platform.posix as m;"
            "f=m.__file__;"
            "s=open(f).read();"
            "old=\\\"env['SHELL']          = 'sh'\\\";"
            "new=\\\"env['SHELL']          = '/system/bin/sh'\\\";"
            "open(f,'w').write(s.replace(old,new) if old in s else s);"
            "print('patched', f if old in s else '(noop)')"
            "\"" % scons_prefix,
            env="build",
        )
        vb = VirtualBuildEnv(self)
        vb.generate()

    def _scons_root(self):
        # Upstream tarball ships SConstruct inside src/ (and get() may or may
        # not strip the root dir depending on layout); locate it robustly.
        for cand in (self.source_folder,
                     os.path.join(self.source_folder, "src"),
                     os.path.join(self.source_folder, "zfs-fuse-0.7.0"),
                     os.path.join(self.source_folder, "zfs-fuse-0.7.0",
                                  "src")):
            if os.path.isfile(os.path.join(cand, "SConstruct")):
                return cand
        raise ConanException(
            "SConstruct not found under %s" % self.source_folder)

    def _scons_cmd(self, extra_args=None):
        # NOTE: run with cwd=<_scons_root()>; `-Y` is SCons --repository,
        # NOT a directory switch.
        python3 = shutil.which("python3") or "python3"
        cmd = [python3, "-m", "SCons", "--jobs=1"]
        cmd += extra_args or []
        return cmd

    # ------------------------------------------------------------------
    # upstream test run (ztest + zdb, R51)
    # ------------------------------------------------------------------

    def _run_upstream_tests(self):
        run_dir = os.path.join(self.build_folder, "zfs-run")
        os.makedirs(run_dir, exist_ok=True)
        env = self._scons_env()
        root = self._scons_root()
        shell = "/bin/sh" if os.path.isfile("/bin/sh") else "/system/bin/sh"
        daemon = os.path.join(root, "zfs-fuse", "zfs-fuse")
        ztest_dir = os.path.join(root, "cmd", "ztest")
        ztest = os.path.join(ztest_dir, "ztest")
        zdb = os.path.join(root, "cmd", "zdb", "zdb")
        for path in (daemon, ztest, zdb):
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                raise ConanException("build product missing: %s" % path)
        pool_dir = os.path.join(run_dir, "ztest-pool")
        os.makedirs(pool_dir, exist_ok=True)
        os.makedirs(os.path.join(run_dir, "mnt"), exist_ok=True)
        daemon_log = os.path.join(run_dir, "zfs-fuse-daemon.log")

        executed = 0
        failed = 0
        notes = []

        # 1) daemon must start and stay up
        with open(daemon_log, "w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [daemon, "--no-daemon", "--no-kstat-mount"],
                cwd=run_dir, env=env,
                stdout=log, stderr=subprocess.STDOUT)
        # 1) daemon must start and stay up (readiness probe: `zpool list`
        #    exit 0 once the socket listener is up)
        daemon_ok = False
        for _ in range(30):
            if proc.poll() is not None:
                break
            probe = subprocess.run(
                [os.path.join(root, "cmd", "zpool",
                                     "zpool"), "list"],
                cwd=run_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", timeout=30)
            if probe.returncode == 0:
                daemon_ok = True
                break
            time.sleep(1)
        if daemon_ok and proc.poll() is None:
            executed += 1
            notes.append("daemon-start=ok")
        else:
            failed += 1
            notes.append("daemon-start=failed")
        # 2) ztest with crash-tolerant passes + zdb verification
        #    (daemon kept up for the zdb label check below)
        ztest_failed = False
        try:
            tproc = subprocess.run(
                [ztest, "-f", pool_dir, "-T", "10"],
                cwd=ztest_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", timeout=600)
            if tproc.returncode == 0:
                executed += 1
                notes.append("ztest=ok")
            else:
                ztest_failed = True
                failed += 1
                notes.append("ztest=failed(rc=%d): %s" % (
                    tproc.returncode,
                    " | ".join((tproc.stdout or "").splitlines()[-3:])))
        except Exception as exc:
            ztest_failed = True
            failed += 1
            notes.append("ztest=error(%r)" % exc)
        # 3) zdb -l label parse on a fresh file vdev (XDR/nvlist smoke);
        #    still needs the daemon for zpool create.
        label_ok = False
        vdev = os.path.join(run_dir, "label.vdev")
        try:
            with open(vdev, "wb") as fh:
                fh.write(b"\0" * (64 * 1024 * 1024))
            if True:
                zpool = os.path.join(root, "cmd", "zpool",
                                     "zpool")
                mk = subprocess.run(
                    [zpool, "create", "-m", "none", "-R", os.path.join(run_dir, "mnt"),
                         "labelpool", vdev],
                    cwd=run_dir, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=120)
                self.output.info("[zpool create] rc=%d: %s" % (
                    mk.returncode, (mk.stdout or "").strip()[:500]))
                if mk.returncode == 0:
                    lb = subprocess.run(
                        [zdb, "-l", vdev],
                        cwd=run_dir, env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        encoding="utf-8", errors="replace")
                    label_ok = ("name: 'labelpool'" in (lb.stdout or ""))
                    subprocess.run(
                        [zpool, "destroy", "-f", "labelpool"],
                        cwd=run_dir, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            notes.append("zdb-label=error(%r)" % exc)
        if label_ok:
            executed += 1
            notes.append("zdb-label=ok")
        elif not ztest_failed:
            failed += 1
            notes.append("zdb-label=failed")
        # terminate the daemon last
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:
            proc.kill()

        status = "passed" if (failed == 0 and executed > 0
                              and daemon_ok) else "failed"
        marker = {
            "status": status,
            "framework": "upstream-ztest",
            "command": "ztest -T 10 + zdb -l + zpool create/destroy",
            "discovered": executed + failed,
            "executed": executed,
            "passed": executed,
            "failed": failed,
            "skipped": 0,
            "notes": notes,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        sys.stdout.flush()
        for note in notes:
            self.output.info("[upstream] %s" % note)
        result_path = os.path.join(self.build_folder,
                                   "upstream_test_result.json")
        try:
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
        except OSError as exc:
            raise ConanException(
                "failed to persist upstream_test_result.json: %s" % exc)
        if status != "passed":
            raise ConanException(
                "upstream zfs-fuse suite failed (%s)" % "; ".join(notes))

    # ------------------------------------------------------------------
    # conan stages
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        self._install_scons()
        root = self._scons_root()
        env = self._scons_env()
        cmd = self._scons_cmd()
        self.output.info("Building zfs-fuse in %s: %s" % (root, " ".join(cmd)))
        subprocess.run(cmd, cwd=root, env=env, check=True)
        self._run_upstream_tests()

    def package(self):
        root = self._scons_root()
        # Binary package: the six CLI tools built by SCons (install_dir).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        products = {
            "zfs-fuse": os.path.join(root, "zfs-fuse",
                                     "zfs-fuse"),
            "zfs": os.path.join(root, "cmd", "zfs", "zfs"),
            "zpool": os.path.join(root, "cmd", "zpool",
                                  "zpool"),
            "zdb": os.path.join(root, "cmd", "zdb", "zdb"),
            "ztest": os.path.join(root, "cmd", "ztest",
                                  "ztest"),
            "zstreamdump": os.path.join(root, "cmd",
                                        "zstreamdump", "zstreamdump"),
        }
        for name, path in products.items():
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                raise ConanException("missing build product %s (%s)"
                                     % (name, path))
            shutil.copy2(path, os.path.join(bindir, name))
        copy(self, "*.8", src=os.path.join(root, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        copy(self, "LICENSE", src=root,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "zfs_pool_alert", src=os.path.join(root,
                                                      "..", "contrib"),
             dst=os.path.join(self.package_folder, "share", "zfs"),
             keep_path=False)
        # Ship the persisted upstream result so test_package can re-emit the
        # identical marker even on conan cache hits ("Already installed!").
        result_path = os.path.join(self.build_folder,
                                   "upstream_test_result.json")
        if os.path.isfile(result_path):
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"),
                 keep_path=False)
        else:
            self.output.warning("upstream_test_result.json missing; package "
                                "will lack upstream evidence")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # Relocatable runtime dirs (patched ohos_paths.c / util.c defaults
        # are /var/run/zfs etc.; consumers may override these env vars).
        self.runenv_info.define("ZFS_SOCK_DIR", "/var/run/zfs")
        self.runenv_info.define("ZPOOL_CACHE_DIR", "/var/lib/zfs")
        self.runenv_info.define("ZFS_LOCK_DIR", "/var/lock/zfs")
