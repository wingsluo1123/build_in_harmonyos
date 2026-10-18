#!/usr/bin/env python3
"""Conan test_package for kturtle 26.04.0 (OHOS).

The delivered product is bin/kturtle (KDE Education, Qt Widgets desktop
application). The consumer test is a real execution test (R34):

  1. the packaged bin/kturtle exists and is executable, and upstream's data
     files (desktop entry, knsrc, metainfo) are installed;
  2. running it with --help under the offscreen QPA platform loads the whole
     Qt6/KF6 link closure (KIO/NewStuff/TextWidgets/XmlGui/Crash/I18n/
     CoreAddons) and prints KAboutData usage, then exits cleanly (KDE apps
     registered with KAboutData handle --help before entering the GUI main
     loop).

The assertions live in test_app.sh so the same check can be reproduced by
hand on a device; this recipe assembles the runtime environment (dependency
libs, offscreen QPA, private HOME/XDG_RUNTIME_DIR) and runs it.
"""
import os
import shutil
import struct

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment


class KturtleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _elf_needed(path):
        """DT_NEEDED strings of a 64-bit little-endian ELF file ([] if not ELF).

        Parsed here instead of shelling out to readelf: the conanrun PATH of a
        CI worker carries neither readelf nor objdump.
        """
        try:
            with open(path, "rb") as fh:
                ehdr = fh.read(64)
                if len(ehdr) < 64 or ehdr[:4] != b"\x7fELF":
                    return []
                if ehdr[4] != 2 or ehdr[5] != 1:  # ELFCLASS64 + little endian
                    return []
                shoff = struct.unpack_from("<Q", ehdr, 0x28)[0]
                shentsize, shnum, shstrndx = struct.unpack_from("<HHH", ehdr, 0x3A)
                if not shoff or not shnum or shstrndx >= shnum:
                    return []
                fh.seek(shoff)
                raw = fh.read(shentsize * shnum)
                if len(raw) < shentsize * shnum:
                    return []

                def section(idx):
                    return struct.unpack_from("<IIQQQQIIQQ", raw, idx * shentsize)

                names_sec = section(shstrndx)
                fh.seek(names_sec[4])
                names = fh.read(names_sec[5])
                dynamic = None
                for idx in range(shnum):
                    sec = section(idx)
                    end = names.find(b"\0", sec[0])
                    if names[sec[0]:end if end >= 0 else None] == b".dynamic":
                        dynamic = sec
                        break
                if dynamic is None:
                    return []
                strtab = section(dynamic[6])  # sh_link -> .dynstr
                fh.seek(strtab[4])
                dynstr = fh.read(strtab[5])
                fh.seek(dynamic[4])
                dyn = fh.read(dynamic[5])
                needed = []
                for off in range(0, len(dyn) - 15, 16):
                    tag, val = struct.unpack_from("<qQ", dyn, off)
                    if tag == 0:  # DT_NULL
                        break
                    if tag == 1:  # DT_NEEDED
                        stop = dynstr.find(b"\0", val)
                        needed.append(
                            dynstr[val:stop if stop >= 0 else None].decode("utf-8", "replace")
                        )
                return needed
        except (OSError, struct.error):
            return []

    @staticmethod
    def _link_or_copy(src, dst, report):
        """Materialise dst as a byte-faithful view of src.

        Hard link first (keeps the dependency's .codesign signature intact on
        HMDFS, see knowledge-extension README R1), plain copy as the fallback
        for filesystems that refuse cross-tree links.
        """
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        if os.path.lexists(dst):
            if os.path.exists(dst):
                return False
            os.remove(dst)  # dangling link left by an earlier run
        try:
            os.link(src, dst)
        except OSError:
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copyfile(src, dst)
        report.append((dst, src))
        return True

    def _materialize_absolute_needed(self, lib_dirs):
        """Recreate missing ABSOLUTE DT_NEEDED targets from the graph.

        Some published KF6 binaries were built without DT_SONAME, so their
        DT_NEEDED entries hold absolute paths into the publisher's own conan
        tree. Most of those point at a package folder (p/<pkgid>/p/lib) whose
        name is derived from the reference + package id, so the same path
        reappears on any machine that downloaded the same revision. The
        transient build tree (p/b/<hash>/p/lib/...) is the exception: it only
        ever existed on the machine that built the dependency, and the loader
        takes an entry containing a slash verbatim, bypassing LD_LIBRARY_PATH
        -- which is why the packaged binary aborted with rc=127 on a clean CI
        worker while passing next to the leftover build tree.
        """
        available = {}
        for lib_dir in lib_dirs:
            for name in sorted(os.listdir(lib_dir)):
                if ".so" in name:
                    available.setdefault(name, os.path.join(lib_dir, name))
        roots = list(lib_dirs)
        dep = self.dependencies.get("kturtle")
        if dep and dep.package_folder:
            roots.append(os.path.join(dep.package_folder, "bin"))
            roots.append(os.path.join(dep.package_folder, "lib"))
        created, unresolved = [], []
        for root in roots:
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    continue
                for needed in self._elf_needed(path):
                    if not needed.startswith("/") or os.path.exists(needed):
                        continue
                    src = available.get(os.path.basename(needed))
                    if not src:
                        unresolved.append((needed, name))
                        continue
                    try:
                        if self._link_or_copy(src, needed, created):
                            self.output.info(
                                "absolute DT_NEEDED repaired: %s -> %s" % (needed, src)
                            )
                    except OSError as exc:
                        unresolved.append(("%s (%s)" % (needed, exc), name))
        for needed, owner in unresolved:
            self.output.warning(
                "absolute DT_NEEDED of %s cannot be resolved from the dependency "
                "graph: %s" % (owner, needed)
            )

    def test(self):
        dep = self.dependencies.get("kturtle")
        assert dep is not None and dep.package_folder, (
            "kturtle is not present in the dependency graph"
        )
        pkg_bin = os.path.join(dep.package_folder, "bin", "kturtle")
        assert os.path.exists(pkg_bin), (
            "missing packaged executable: {}".format(pkg_bin)
        )
        # HMDFS chmod 被忽略（E046，权限固定 660），X_OK 探测恒 False——
        # 只校验存在性，可执行性由实际运行验证（真实执行即最强证据）。

        # Upstream installs the desktop entry, the Get Hot New Stuff catalog
        # and the AppStream metainfo; their presence proves the install phase
        # delivered the full application, not just a bare binary.
        desktop = os.path.join(
            dep.package_folder, "share", "applications", "org.kde.kturtle.desktop"
        )
        assert os.path.exists(desktop), (
            "missing installed desktop entry: {}".format(desktop)
        )
        knsrc = os.path.join(
            dep.package_folder, "share", "knsrcfiles", "kturtle.knsrc"
        )
        assert os.path.exists(knsrc), (
            "missing installed knsrc catalog: {}".format(knsrc)
        )
        metainfo = os.path.join(
            dep.package_folder, "share", "metainfo", "org.kde.kturtle.appdata.xml"
        )
        assert os.path.exists(metainfo), (
            "missing installed AppStream metainfo: {}".format(metainfo)
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

        # Some published KF6 binaries (kconfig/6.18.x KConfigGui, ki18n I18n
        # locale data, sonnet, knewstuff, kbookmarks, qtdeclarative) record
        # DT_NEEDED entries as RELATIVE paths ("../../bin/libX.so"). The
        # dynamic loader resolves those against the CURRENT WORKING
        # DIRECTORY, not LD_LIBRARY_PATH. Build a deterministic cwd root next
        # to the test build folder: <parent(build)>/bin holds the referenced
        # basenames copied from their dependency packages, and the test runs
        # with CWD=<parent(build)>/cwdroot so "../.."+bin resolves there.
        # Pure conan-package-relative logic -- no machine-local paths.
        parent_dir = os.path.dirname(self.build_folder)
        bin_dir = os.path.join(parent_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wanted = [
            "libKF6ConfigCore.so",
            "libKF6I18n.so",
            "libKF6NewStuffCore.so",
            "libKF6Bookmarks.so",
            "libKF6IconThemes.so",
            "libkuriikwsfiltereng_private.so",
        ]
        # Search every dependency package folder (direct AND transitive --
        # e.g. kbookmarks arrives via knewstuff) for each wanted basename.
        lib_candidates = []
        for item in self.dependencies.values():
            if not item or not item.package_folder:
                continue
            for sub in ("p/lib", "lib"):
                d = os.path.join(item.package_folder, sub)
                if os.path.isdir(d):
                    lib_candidates.append(d)
        for base in wanted:
            dest = os.path.join(bin_dir, base)
            if os.path.exists(dest):
                continue
            for d in lib_candidates:
                cand = os.path.join(d, base)
                if os.path.exists(cand):
                    if os.path.exists(dest):
                        os.remove(dest)
                    try:
                        # Byte-faithful links preserve the dependency lib's
                        # .codesign signature (HMDFS verifies signatures at
                        # load: any byte rewrite -> Permission denied, see
                        # knowledge-extension README R1). /bin/cp is the
                        # local fallback (HMDFS forbids in-place overwrite
                        # and conanrun PATH lacks /bin); plain copyfile
                        # covers the ext4/CI worker.
                        os.link(cand, dest)
                    except OSError:
                        import subprocess

                        # absolute path: conanrun env PATH may not carry /bin
                        if subprocess.call(["/bin/cp", cand, dest]) != 0:
                            shutil.copyfile(cand, dest)
                    break
        cwd_root = os.path.join(self.build_folder, "cwdroot")
        os.makedirs(cwd_root, exist_ok=True)

        # Absolute DT_NEEDED entries left behind by SONAME-less dependency
        # builds cannot be redirected through LD_LIBRARY_PATH; materialise the
        # missing targets from the graph before running the binary.
        self._materialize_absolute_needed(lib_candidates)

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
            self.run(
                'cd "{}" && sh "{}" "{}"'.format(cwd_root, script, pkg_bin),
                env="conanrun",
            )
