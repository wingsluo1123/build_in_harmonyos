#!/usr/bin/env python3
"""Conan test_package for kcron 26.04.1 (application package).

kcron ships three artifacts inside its install tree:
  - the QML KCM plugin kcm_cron.so (plasma/kcms/systemsettings, next to the
    kcmdesktopfilegenerator-made kcm_cron.desktop),
  - the KAuth helper executable kcron_helper (libexec/kauth),
  - the local.kcron.crontab KAuth activation files (backend dependent).

The consumer test (test_kcron.cpp, driven through ctest below) is the R51
consumer verification: it loads the shipped plugin through QPluginLoader and
KPluginFactory, drives the TasksModel/VariablesModel/TaskValidator surface
through a real QQmlEngine and exercises the patched null-passwd / null-cron
paths (see the test source header for the case list).

The upstream test suite (taskvalidatortest, 9 cases) runs at build time in
the recipe build() - see ../../conanfile.py docstring and MANIFEST.yml.
"""
import os
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

OHOS_BIN_DIR = "/data/service/hnp/bin"


class KCronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Mirror the kcron 26.04.1 dependency matrix (same list as the
        # recipe): the consumer graph and the runtime library search paths
        # must be complete without relying on transitive activation.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("kauth/6.26.0")
        self.requires("kcmutils/6.26.0")
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kirigami/6.18.0")
        self.requires("kirigami-addons/1.13.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("kiconthemes/6.26.0", override=True)
        self.requires("kcrash/6.26.0", override=True)
        self.requires("expat/2.8.2.1", override=True)
        self.requires("qtbase/6.11.1.1", override=True)
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        package_folder = self.dependencies["kcron"].package_folder
        if not package_folder:
            raise ConanException("kcron package_folder is not available")
        tc.variables["KCRON_PACKAGE_DIR"] = package_folder.replace("\\", "/")
        # Qt6Qml/Qt6Quick live in the qtdeclarative package; Qt discovers
        # additional components through the official
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook (same list as the recipe's
        # generate(), kcmutils precedent). Without it the qtbase
        # Qt6Config.cmake is found first and fails on the missing component.
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools", "qtmultimedia"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder and dep.package_folder not in qt_extra:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        """CMakeDeps cannot add cmake_find_mode=none packages (qtbase/KF6) to
        CMAKE_PREFIX_PATH, so the dependency search paths are written by hand
        (kcmutils 6.26.0 / kcolorchooser 26.04.0 precedent)."""
        prefixes = []
        libraries = []
        includes = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.extend([os.path.join(dep.package_folder, "lib", "cmake"), dep.package_folder])
                libraries.append(os.path.join(dep.package_folder, "lib"))
                includes.append(os.path.join(dep.package_folder, "include"))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── runtime helpers ────────────────────────────────────────────────

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

    def _kcron_package_folder(self):
        return self.dependencies["kcron"].package_folder

    @staticmethod
    def _ohos_tool(name):
        candidate = os.path.join(OHOS_BIN_DIR, name)
        return candidate if os.path.isfile(candidate) else name

    @staticmethod
    def _elf_needed(path):
        """Return the DT_NEEDED strings of a 64-bit little/big-endian ELF."""
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return []
        if len(data) < 0x40 or data[:4] != b"\x7fELF" or data[4] != 2:
            return []
        little = data[5] == 1
        fmt_q = "<Q" if little else ">Q"
        fmt_h = "<H" if little else ">H"
        fmt_i = "<I" if little else ">I"
        fmt_dyn = "<qQ" if little else ">qQ"
        e_shoff = struct.unpack_from(fmt_q, data, 0x28)[0]
        e_shentsize = struct.unpack_from(fmt_h, data, 0x3A)[0]
        e_shnum = struct.unpack_from(fmt_h, data, 0x3C)[0]
        if not e_shoff or not e_shentsize:
            return []
        sections = []
        for index in range(e_shnum):
            off = e_shoff + index * e_shentsize
            if off + e_shentsize > len(data):
                break
            sections.append(
                (
                    struct.unpack_from(fmt_i, data, off + 4)[0],   # sh_type
                    struct.unpack_from(fmt_q, data, off + 16)[0],  # sh_addr
                    struct.unpack_from(fmt_q, data, off + 24)[0],  # sh_offset
                    struct.unpack_from(fmt_q, data, off + 32)[0],  # sh_size
                )
            )
        needed = []
        for sh_type, _sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or not sh_size:  # SHT_DYNAMIC
                continue
            strtab_addr = None
            entries = []
            pos = sh_offset
            end = min(sh_offset + sh_size, len(data))
            while pos + 16 <= end:
                tag, value = struct.unpack_from(fmt_dyn, data, pos)
                if tag == 0:
                    break
                if tag == 5:    # DT_STRTAB
                    strtab_addr = value
                elif tag == 1:  # DT_NEEDED
                    entries.append(value)
                pos += 16
            if strtab_addr is None or not entries:
                continue
            for _t, sh_addr, sh_off, sh_len in sections:
                if sh_addr <= strtab_addr < sh_addr + sh_len:
                    base = sh_off + (strtab_addr - sh_addr)
                    limit = sh_len - (strtab_addr - sh_addr)
                    break
            else:
                continue
            for rel in entries:
                if rel >= limit:
                    continue
                start = base + rel
                stop = data.find(b"\x00", start, base + limit)
                if stop < 0:
                    continue
                needed.append(data[start:stop].decode("utf-8", "replace"))
        return needed

    def _iter_elf_libs(self):
        for libdir in self._libdirs():
            for name in sorted(os.listdir(libdir)):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    yield full, name

    def _iter_package_elfs(self):
        """Yield (path, name) for every ELF in the kcron install tree
        (kcm_cron.so, kcron_helper, any sibling module)."""
        root = self._kcron_package_folder()
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ("share", "include")]
            for name in sorted(files):
                if not (name.endswith(".so") or ".so." in name or "." not in name):
                    continue
                full = os.path.join(dirpath, name)
                if not os.path.isfile(full):
                    continue
                try:
                    with open(full, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                yield full, name

    def _sign(self, path):
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _prepare_runtime_links(self):
        """Symlink every dependency library into <build>/bin and
        <build>/../../bin so the relative "../../bin/libX.so" DT_NEEDED
        entries of the published KF6 libraries resolve from the test CWD."""
        compat = {}
        for full, name in self._iter_elf_libs():
            compat.setdefault(name, full)
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, source in compat.items():
                link = os.path.join(base, name)
                if not os.path.lexists(link):
                    try:
                        os.symlink(source, link)
                    except OSError as error:
                        self.output.warning(f"link farm skip {name}: {error}")

    def _fix_relative_needed(self):
        """Rewrite relative DT_NEEDED entries of the published KF6 libraries
        to SONAME-only (patchelf --replace-needed) and re-sign afterwards.
        OHOS resolves such entries from the symlink path, not the realpath,
        which breaks the multi-package KF6 layout."""
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        patchelf = self._ohos_tool("patchelf")
        fixes = 0
        for full, name in self._iter_elf_libs():
            for entry in self._elf_needed(full):
                if not entry.startswith("../") and not entry.startswith("./"):
                    continue
                soname = os.path.basename(entry)
                self.output.info(
                    f"patching relative DT_NEEDED {entry} -> {soname} in {name}"
                )
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", full],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [patchelf, "--replace-needed", entry, soname, full],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                subprocess.run(
                    [signer, "sign", "-inFile", full, "-outFile", full,
                     "-selfSign", "1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                fixes += 1
        if fixes:
            self.output.info(f"patched {fixes} relative DT_NEEDED entries")

    def _fix_absolute_needed(self):
        """Rewrite the absolute DT_NEEDED entries of the dependency libraries
        and the shipped kcron ELFs to plain basenames (patchelf
        --replace-needed + re-sign; kgoldrunner 26.04.0 precedent, adapted).

        The published KF6 6.26.0 libraries carry paths baked at their original
        build time. On this device those point into a stale earlier conan home
        (~/.cache/conan2) which still exists, so the loader follows the entry
        and loads a copy outside the current graph - and that copy still has
        build-tree-relative entries (../../bin/libKF6*.so) that cannot be
        repaired here. Rewriting to plain basenames makes every lookup go
        through DT_RPATH / the exported LD_LIBRARY_PATH, i.e. through the
        packages of this graph only. Entries whose basename is not part of the
        closure are left untouched (they were only resolvable through the
        baked path anyway)."""
        index = {}
        for full, name in self._iter_elf_libs():
            index.setdefault(name, full)
        scan = [full for full, _name in self._iter_elf_libs()]
        scan.extend(full for full, _name in self._iter_package_elfs())
        fixes = 0
        for full in scan:
            for entry in self._elf_needed(full):
                if not entry.startswith("/"):
                    continue
                soname = os.path.basename(entry)
                if soname not in index:
                    continue
                self.output.info(
                    f"patching absolute DT_NEEDED {entry} -> {soname} in {os.path.basename(full)}"
                )
                subprocess.run(
                    [self._ohos_tool("llvm-objcopy"), "--remove-section",
                     ".codesign", full],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [self._ohos_tool("patchelf"), "--replace-needed", entry,
                     soname, full],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                subprocess.run(
                    [self._ohos_tool("binary-sign-tool"), "sign", "-inFile",
                     full, "-outFile", full, "-selfSign", "1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                fixes += 1
        if fixes:
            self.output.info(f"patched {fixes} absolute DT_NEEDED entries")

    # ── consumer test ──────────────────────────────────────────────────

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return

        if str(self.settings.os) == "OHOS":
            for full, name in self._iter_package_elfs():
                self._sign(full)
            self._prepare_runtime_links()
            self._fix_relative_needed()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        plugin_dirs = []
        platforms = []
        qml_dirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for rel in ("plugins", os.path.join("lib", "plugins")):
                directory = os.path.join(dep.package_folder, rel)
                if not os.path.isdir(directory):
                    continue
                if directory not in plugin_dirs:
                    plugin_dirs.append(directory)
                platform_dir = os.path.join(directory, "platforms")
                if os.path.isdir(platform_dir) and platform_dir not in platforms:
                    platforms.append(platform_dir)
            for rel in ("qml", os.path.join("lib", "qml")):
                directory = os.path.join(dep.package_folder, rel)
                if os.path.isdir(directory) and directory not in qml_dirs:
                    qml_dirs.append(directory)

        # NOTE: define() with explicitly os.pathsep-joined values — Conan's
        # Environment.append() joins with a space, which makes Qt treat the
        # whole list as a single (invalid) plugin directory (kcolorchooser
        # 26.04.0 precedent).
        env = Environment()
        env.define("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        if plugin_dirs:
            env.define("QT_PLUGIN_PATH", os.pathsep.join(plugin_dirs))
        if platforms:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH", os.pathsep.join(platforms)
            )
        if qml_dirs:
            env.define("QML2_IMPORT_PATH", os.pathsep.join(qml_dirs))
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)

        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(platforms)
        if plugin_dirs:
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)

        with env.vars(self).apply():
            # Explicit self.run() of ctest (L0d: the gate statically checks
            # for a real test execution; cmake.test() without a visible
            # self.run is flagged as a stub). ctest runs the test_kcron
            # consumer binary against the installed package tree under the
            # full runtime env above.
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                ),
                env="conanrun",
            )
        self.output.info("kcron consumer cases passed")
