#!/usr/bin/env python3
"""Conan test_package for kmag 26.04.0 (application package).

KMagnifier is a GUI application. Upstream ships no tests at all (no
tests/ directory, no add_test/ctest registration, no QTEST macro), so the
R51 verification is this self-authored consumer test:

  1. the installed application binary runs --version (KAboutData /
     KLocalizedString / QApplication initialization path) and prints the
     26.04.0 version string;
  2. --help prints the KAboutData usage banner (QCommandLineParser path
     before the main window is created), headless-safe offscreen;
  3. qimage_smoke (compiled by this test_package against the package's
     Qt6 Gui) reproduces the snapshot export path of the application:
     render a QImage with QPainter, write it through QImageWriter as PNG
     to a temporary file, read it back with QImageReader and verify the
     size and pixel content - the same QImageWriter/QTemporaryFile flow
     that saveZoomPixmap() uses before handing the file to KIO.

test.sh is the POSIX-shell executor: every case prints TEST PASS / TEST
FAIL independently, the run ends with a TEST SUMMARY line, and any
failure makes the process exit 1.

Runtime environment (ksystemlog 26.04.0 precedent):
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so") are resolved through compatibility symlink
    farms at <build>/bin and <build>/../../bin (the OHOS musl loader
    resolves path-style NEEDED entries relative to the process cwd);
  - build-machine absolute DT_NEEDED entries get an absolute fallback
    layer: the missing paths are created as symlinks to the real
    libraries found in the dependency packages;
  - /system/lib64 for the compatible libc++_shared.so;
  - the OHOS binary signature is refreshed before execution (freshly
    built executables need a .codesign section to be executable).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KmagTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Full transitive runtime DT_NEEDED closure of the kmag binary
        # (the published KF6 recipes do not propagate a runenv into the
        # consumer graph, so they are declared here for the lib-dir
        # collection - ksystemlog test_package precedent).
        self.requires("qtbase/6.11.1")
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kcrash/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("kiconthemes/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("karchive/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake has no HarmonyOS platform module (kmousetool precedent).
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"

        # qtbase uses cmake_find_mode=none, so CMakeDeps does not generate
        # conan_cmakedeps_paths.cmake. Write it manually (kmousetool
        # test_package precedent).
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    lib_dirs.append(lib_dir)
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Runtime search path for the smoke executable: every dependency
        # lib dir plus /system/lib64 for the compatible libc++_shared.so.
        rpath = ";".join(["/system/lib64"] + lib_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = rpath
        tc.variables["CMAKE_INSTALL_RPATH"] = rpath
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

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
        """Compatibility symlink farms for relative DT_NEEDED entries baked
        into the published KF6 packages ("../../bin/libKF6*.so" and
        "../../bin/libzstd.so.1" relative to the process cwd)."""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    full = os.path.join(libdir, name)
                    real = (
                        os.path.realpath(full)
                        if os.path.islink(full)
                        else full
                    )
                    compat_libs.setdefault(name, real)
        home = os.path.abspath(os.path.expanduser("~"))
        home_prefix = home + os.sep
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            base = os.path.abspath(base)
            if base != home and not base.startswith(home_prefix):
                self.output.warning(
                    f"skip runtime-link farm outside home: {base}")
                continue
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_absolute_needed(self):
        """Create the missing absolute DT_NEEDED paths of the published
        packages as symlinks to the real libraries in the dependency
        packages (the OHOS musl loader resolves path-style NEEDED entries
        literally, with no LD_LIBRARY_PATH fallback)."""
        import struct

        def elf_needed(path):
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
                return []
            is_le = data[5] == 1
            e_shoff = struct.unpack_from(
                "<Q" if is_le else ">Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3A)[0]
            e_shnum = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3C)[0]
            if e_shoff + e_shnum * e_shentsize > len(data):
                return []

            def sh_field(i, fmt, byteoff):
                off = e_shoff + i * e_shentsize + byteoff
                if off + struct.calcsize(fmt) > len(data):
                    return None
                return struct.unpack_from(
                    "<" + fmt if is_le else ">" + fmt, data, off)[0]

            dyn_idx, dyn_off, dyn_size = None, None, None
            for i in range(e_shnum):
                if sh_field(i, "H", 4) == 6:  # SHT_DYNAMIC
                    dyn_idx = i
                    dyn_off = sh_field(i, "Q", 0x18)
                    dyn_size = sh_field(i, "Q", 0x20)
                    break
            if dyn_idx is None or dyn_off is None or dyn_size is None:
                return []
            dynstr_off = sh_field(dyn_idx, "I", 0x28)  # sh_link
            if dynstr_off is None or dynstr_off >= e_shnum:
                return []
            dynstr = sh_field(dynstr_off, "Q", 0x18)
            if dynstr is None:
                return []
            needed = []
            p, end = dyn_off, dyn_off + dyn_size
            while p + 16 <= end and p + 16 <= len(data):
                tag, val = struct.unpack_from(
                    "<QQ" if is_le else ">QQ", data, p)
                if tag == 0:
                    break
                if tag == 1:  # DT_NEEDED
                    s = dynstr + val
                    e = data.find(b"\x00", s)
                    if e == -1:
                        break
                    needed.append(data[s:e].decode("utf-8", "replace"))
                p += 16
            return needed

        index = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        # DT_NEEDED strings come from externally published ELF files, so
        # only ever materialize paths inside a Conan cache root (the
        # published KF6 packages record the build worker's cache root:
        # $HOME/.cache/conan2/p/<pkg>/p/lib/...). Anything else is skipped
        # instead of creating directories and symlinks in arbitrary
        # locations (an entry under $HOME/.ssh would previously pass).
        home = os.path.realpath(os.path.expanduser("~"))
        allowed_roots = [
            os.path.join(home, ".cache", "conan2"),
            os.path.join(home, ".conan2"),
        ]
        conan_home = os.environ.get("CONAN_HOME", "").strip()
        if conan_home:
            allowed_roots.append(os.path.realpath(conan_home))
        allowed_prefixes = tuple(
            os.path.join(os.path.realpath(r), "") for r in allowed_roots
        )

        fixes = 0
        scan_roots = list(self._libdirs())
        pkg_bin = None
        pkg = self.dependencies.get("kmag")
        if pkg and pkg.package_folder:
            pkg_bin = os.path.join(pkg.package_folder, "bin")
            if os.path.isdir(pkg_bin):
                scan_roots.append(pkg_bin)
        seen_files = set()
        for root in scan_roots:
            for name in os.listdir(root):
                full = os.path.join(root, name)
                if not os.path.isfile(full):
                    continue
                # A .so/.so.N symlink chain points at one physical ELF
                # file; parse each real file once (G finding: the same
                # library was parsed 2-3 times through its aliases).
                real = os.path.realpath(full)
                if real in seen_files:
                    continue
                seen_files.add(real)
                is_elfish = name.endswith(".so") or ".so." in name
                if root != pkg_bin and not is_elfish:
                    continue
                for entry in elf_needed(full):
                    if not entry.startswith("/"):
                        continue
                    entry = os.path.normpath(entry)
                    if not entry.startswith(allowed_prefixes):
                        self.output.warning(
                            f"skip absolute NEEDED outside conan cache: {entry}")
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
                            os.symlink(source, entry)
                            fixes += 1
                    except OSError as e:
                        self.output.warning(
                            f"cannot create NEEDED fallback {entry}: {e}")
        if fixes:
            self.output.info(
                f"created {fixes} absolute-NEEDED compatibility symlinks")

    def _sign(self, path):
        import subprocess
        objcopy = os.environ.get(
            "OHOS_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get(
            "OHOS_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise RuntimeError(f"OHOS signing tool not found: {tool}")
        # Sign a sibling copy and swap it in only after both tools
        # succeed. Signing rewrites the file in place, so a failure
        # between objcopy and binary-sign-tool would otherwise leave the
        # package-cache binary stripped of its .codesign section and
        # unusable for every later consumer.
        mode = os.stat(path).st_mode
        tmp = path + ".codesign-tmp"
        shutil.copy2(path, tmp)
        try:
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp],
                           check=True)
            subprocess.run([signer, "sign", "-inFile", tmp, "-outFile", tmp,
                            "-selfSign", "1"], check=True)
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        finally:
            if os.path.lexists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["kmag"]
        gui = os.path.join(pkg.package_folder, "bin", "kmag")
        if not os.path.isfile(gui):
            raise RuntimeError(f"kmag binary not found: {gui}")

        smoke = os.path.join(self.cpp.build.bindir, "qimage_smoke")
        if not os.path.isfile(smoke):
            raise RuntimeError(f"qimage_smoke not built: {smoke}")

        if str(self.settings.os) == "OHOS":
            self._sign(gui)
            self._sign(smoke)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

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

        # QT_QPA_PLATFORM_PLUGIN_PATH is a single directory, not a
        # path list: joining several entries makes Qt treat the whole
        # string as one non-existent directory. Pick the directory that
        # actually ships the offscreen plugin.
        plugin_dirs = list(dict.fromkeys(plugin_dirs))
        platforms = list(dict.fromkeys(platforms))
        qpa_plugin_dir = ""
        for d in platforms:
            if os.path.isfile(os.path.join(d, "libqoffscreen.so")):
                qpa_plugin_dir = d
                break
        if not qpa_plugin_dir and platforms:
            qpa_plugin_dir = platforms[0]

        env = Environment()
        env.append("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QT_PLUGIN_PATH", os.pathsep.join(plugin_dirs))
        if qpa_plugin_dir:
            env.define("QT_QPA_PLATFORM_PLUGIN_PATH", qpa_plugin_dir)
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)
        env.define("XDG_CACHE_HOME", os.path.join(self.build_folder, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(self.build_folder, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(self.build_folder, ".local", "share"))

        # conan's self.run() may spawn a fresh shell environment that
        # drops the appended loader vars; persist them via os.environ so
        # the subprocess inherits them (ksystemlog test_package precedent).
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)
        if qpa_plugin_dir:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qpa_plugin_dir
        os.environ["HOME"] = self.build_folder
        os.environ["XDG_RUNTIME_DIR"] = self.build_folder

        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            self.run(
                f'{shlex.quote(shell)} '
                f'{shlex.quote(os.path.join(self.source_folder, "test.sh"))} '
                f'{shlex.quote(gui)} {shlex.quote(smoke)}',
                cwd=self.build_folder,
            )
        self.output.info("kmag consumer tests passed")
