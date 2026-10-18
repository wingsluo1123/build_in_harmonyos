#!/usr/bin/env python3
"""Conan recipe for libkdegames 24.12.3 on HarmonyOS PC (aarch64).

libkdegames is the shared library used by KDE games (kfourinline, etc.).
Upstream 24.12.3 (KDE Gear 24.12 branch) is a Qt6/KF6 based CMake project
(ECM toolchain): QT_MIN_VERSION 6.5.0, KF_MIN_VERSION 6.0.0.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a full gettext toolchain not needed for the library)
  - BUILD_SVG_CHECKS=OFF (default) so carddecks SVG processing only needs
    gzip; svgcleaner/7zip stay optional and are not used
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1,
    qtdeclarative 6.11.1 (Qt6::Qml/Quick), qtsvg 6.11.1 (Qt6::Svg),
    KF6 6.18.0 framework set + kdnssd 6.29.0, openal-soft 1.25.2,
    libsndfile 1.2.2, ecm 6.26.0 (tool_requires)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH
  - Upstream ctest suite (tests/ + src/private/tests/, BUILD_TESTING=ON)
    is executed inside the build with an offscreen Qt platform and a
    sandboxed XDG/HOME tree
"""
import os
import glob
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkdegamesConan(ConanFile):
    name = "libkdegames"
    version = "24.12.3"
    description = (
        "KDE games shared library - common code for KDE games "
        "(KGameRenderer, KGameTheme, highscore framework, kgamedialog, audio)"
    )
    license = "LGPL-2.0-only"
    homepage = "https://invent.kde.org/games/libkdegames"
    url = "https://invent.kde.org/games/libkdegames"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        # karchive: force the 6.18.0 line for the whole graph. The newest
        # kiconthemes/6.18.0 recipe revision requires karchive/6.19.0, which
        # conflicts with knewstuff/6.18.0 (karchive/6.18.0). Override pins the
        # compatible 6.18.0 so the KF6 6.18 closure stays consistent.
        self.requires("karchive/6.18.0", override=True)
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kdnssd/6.29.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("knewstuff/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing is not needed for the library itself.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS",):
            # CMake has no Platform/HarmonyOS module, so
            # CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG stay undefined and
            # shared libraries are linked without -Wl,-soname: consumers then
            # record build-machine paths in DT_NEEDED and L5 fails. Define the
            # flags explicitly and keep the SONAME unversioned.
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtshadertools", "qtsvg"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        # Direct dependencies are not enough: the shipped KF6 config files pull
        # their own requirements through find_dependency (KF6ConfigWidgets ->
        # KF6WidgetsAddons, KF6NewStuffCore -> KF6Attica), and qtbase/KF6 are
        # packaged with cmake_find_mode=none so CMakeDeps never puts them on the
        # prefix path. Walk the whole host+build graph instead.
        seen = set()
        for dep in self._walk_dependencies(self.dependencies) + self._walk_dependencies(
            self.dependencies.build
        ):
            ref = dep.ref
            key = "{}/{}".format(ref.name, ref.version)
            if key in seen or not dep.package_folder:
                continue
            seen.add(key)
            self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _walk_dependencies(self, deps):
        """Depth-first walk over the dependency graph (direct deps only per level)."""
        result = []
        try:
            direct = list(deps.values())
        except Exception:
            return result
        for dep in direct:
            result.append(dep)
            nested = getattr(dep, "dependencies", None)
            if nested is None:
                continue
            try:
                result.extend(self._walk_dependencies(nested))
            except Exception:
                continue
        return result

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _sanitize_needed_entries(self):
        # The published KF6 6.18.0 dependency artifacts carry no DT_SONAME
        # (same Platform/HarmonyOS gap), so this package's shared libraries
        # record the absolute conan-cache paths of those dependencies in
        # DT_NEEDED and the artifact is not portable (loader error outside
        # the build machine, L5 soname gate failure). Rewrite such path-form
        # DT_NEEDED entries to plain basenames so the loader resolves them
        # through LD_LIBRARY_PATH / the runenv, which this recipe and its
        # consumers provide. Only path-form entries are touched; plain
        # soname-form entries (libQt6Core.so.6, libc.so, ...) are left alone.
        #
        # The rewrite is a minimal in-place .dynstr byte patch (the
        # replacement basename is always shorter than the path-form entry,
        # so the string table size and every other ELF structure stay
        # untouched). patchelf --replace-needed was tried first, but it
        # rewrites the whole program header table and the result is rejected
        # by the OHOS musl loader, so it must not be used here.
        if str(self.settings.os) not in ("OHOS",):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        replaced = 0
        for name in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, name)
            if not name.endswith(".so") and ".so." not in name:
                continue
            if not self._is_elf(path):
                self.output.warning(f"{name}: not an ELF, skipped")
                continue
            replaced += self._patch_needed_paths_in_place(path)
        if replaced:
            self.output.info(f"DT_NEEDED entries sanitized: {replaced}")
        remaining = [
            name
            for name in sorted(os.listdir(libdir))
            if (name.endswith(".so") or ".so." in name)
            and self._is_elf(os.path.join(libdir, name))
            and self._has_path_form_needed(os.path.join(libdir, name))
        ]
        if remaining:
            raise ConanException(
                "path-form DT_NEEDED left in: " + ", ".join(remaining)
            )

    @staticmethod
    def _elf_needed_patch(data):
        """In-place rewrite of path-form DT_NEEDED strings in an ELF.

        Returns (data, replaced_count). Only DT_NEEDED entries are touched;
        DT_SONAME / DT_RPATH / DT_RUNPATH keep their original values (an
        RPATH is a colon-separated list, so truncating it to a basename
        would silently break library lookup). Only bytes inside .dynstr are
        modified; every other byte of the file is preserved exactly.
        """
        if data[:4] != b"\x7fELF":
            return data, 0
        ei_class = data[4]
        ei_data = data[5]
        if ei_class != 2 or ei_data != 1:  # ELFCLASS64, little-endian only
            return data, 0
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0:
            return data, 0

        sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_addr = struct.unpack_from("<Q", data, off + 16)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 24)[0]
            sh_size = struct.unpack_from("<Q", data, off + 32)[0]
            sections.append((sh_type, sh_addr, sh_offset, sh_size))

        buf = bytearray(data)
        replaced = 0
        for sh_type, sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or sh_size == 0:  # SHT_DYNAMIC
                continue
            strtab_addr = None
            strtab_size = None
            needed_offsets = []
            used_offsets = set()
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 5:  # DT_STRTAB
                    strtab_addr = d_val
                elif d_tag == 10:  # DT_STRSZ
                    strtab_size = d_val
                elif d_tag == 1:  # DT_NEEDED
                    needed_offsets.append(d_val)
                    used_offsets.add(d_val)
                elif d_tag in (14, 15, 29):  # SONAME/RPATH/RUNPATH
                    # Kept verbatim, but their offsets still matter for the
                    # suffix-sharing guard below.
                    used_offsets.add(d_val)
                elif 0 < d_val < 0x100000:
                    # Any other dynamic value could double as a string
                    # pointer; treat it conservatively for collisions.
                    used_offsets.add(d_val)
            if strtab_addr is None or not needed_offsets:
                continue
            strtab_off = None
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 in (3, 6, 7, 1):
                    strtab_off = sh_offset2
                    strtab_size = min(strtab_size or sh_size2, sh_size2)
                    break
            if strtab_off is None:
                continue
            strtab = bytes(buf[strtab_off:strtab_off + (strtab_size or 0)])
            for off in needed_offsets:
                if off >= len(strtab):
                    continue
                end = strtab.find(b"\x00", off)
                if end < 0:
                    continue
                old = strtab[off:end]
                if b"/" not in old:
                    continue
                base = old.rsplit(b"/", 1)[1]
                # Refuse to write if another dynamic string starts inside
                # the region we would overwrite (suffix sharing).
                if any(off < u < end for u in used_offsets):
                    continue
                new = base + b"\x00" * (len(old) - len(base))
                buf[strtab_off + off:strtab_off + end] = new
                replaced += 1
        return bytes(buf), replaced

    @classmethod
    def _has_path_form_needed(cls, path):
        with open(path, "rb") as handle:
            data = handle.read()
        _, count = cls._elf_needed_patch(data)
        return count > 0

    def _patch_needed_paths_in_place(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        patched, count = self._elf_needed_patch(data)
        if not count:
            return 0
        with open(path, "wb") as handle:
            handle.write(patched)
        self.output.info(f"NEEDED sanitized in {os.path.basename(path)}: {count}")
        # OHOS enforces valid ELF code signatures (.codesign section): a
        # rewritten file is refused by the loader with EACCES until it is
        # re-signed. If signing is not possible, roll the rewrite back
        # instead of shipping a library the device cannot load.
        if not self._resign_elf(path):
            with open(path, "wb") as handle:
                handle.write(data)
            raise ConanException(
                f"{os.path.basename(path)}: DT_NEEDED rewrite cannot be "
                "re-signed (llvm-objcopy/binary-sign-tool unavailable or "
                "failed); rolled back. Install the OHOS signing tools or "
                "pass -c tools.build:compiler_executables so they are found."
            )
        return count

    def _resign_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "llvm-objcopy/binary-sign-tool not found; "
                f"{path} stays without a fresh signature and may not load"
            )
            return False
        mode = os.stat(path).st_mode & 0o777
        signed = path + ".signed"
        probe = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            self.output.warning(
                f"llvm-objcopy --remove-section .codesign failed for {path}: "
                f"{probe.stderr.strip()[:120]}"
            )
            return False
        probe = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            self.output.warning(
                f"binary-sign-tool sign failed for {path}: "
                f"{probe.stderr.strip()[:120]}"
            )
            return False
        shutil.move(signed, path)
        os.chmod(path, mode)
        return True

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("TMPDIR", test_tmp)
        test_env.define("TEMP", test_tmp)
        test_env.define("TMP", test_tmp)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        self._prepare_needed_compatibility_links((self.build_folder,))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def _runtime_elf_roots(self, extra_roots=()):
        roots = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                roots.append(os.path.join(dep.package_folder, "lib"))
                roots.append(os.path.join(dep.package_folder, "bin"))
        roots.extend(root for root in extra_roots if root)

        seen = set()
        for root in roots:
            normalized = os.path.normpath(root)
            if normalized in seen:
                continue
            seen.add(normalized)
            yield normalized

    def _runtime_library_map(self, extra_roots=()):
        libraries = {}
        for root in self._runtime_elf_roots(extra_roots):
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
                for name in files:
                    path = os.path.join(current, name)
                    if os.path.isfile(path) and (".so" in name or name.startswith("lib")):
                        libraries.setdefault(name, path)
        return libraries

    def _iter_runtime_elfs(self, extra_roots=()):
        for root in self._runtime_elf_roots(extra_roots):
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
                for name in files:
                    path = os.path.join(current, name)
                    if self._is_elf(path):
                        yield path

    def _needed_entries(self, readelf, elf_path):
        try:
            probe = subprocess.run(
                [readelf, "-d", elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError as exc:
            self.output.warning(f"readelf failed for {elf_path}: {exc}")
            return []
        if probe.returncode != 0:
            return []
        entries = []
        marker = "Shared library: ["
        for line in probe.stdout.splitlines():
            if marker in line:
                entries.append(line.split(marker, 1)[1].split("]", 1)[0])
        return entries

    @staticmethod
    def _is_conan_cache_needed_path(needed):
        return os.path.isabs(needed) and "/.cache/conan2/" in needed.replace("\\", "/")

    @staticmethod
    def _is_relative_needed_path(needed):
        return not os.path.isabs(needed) and "/" in needed.replace("\\", "/")

    def _link_needed_library(self, source, target):
        if os.path.lexists(target):
            try:
                if os.path.exists(target) and os.path.samefile(source, target):
                    return False
            except OSError:
                pass
            if os.path.exists(target) and not os.path.islink(target):
                return False
            os.unlink(target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            os.symlink(source, target)
        except OSError:
            shutil.copy2(source, target)
        return True

    def _prepare_needed_compatibility_links(self, extra_roots=()):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_ohos_tool("llvm-readelf") or self._find_ohos_tool("readelf")
        if not readelf:
            self.output.warning("llvm-readelf/readelf not found; skip NEEDED links")
            return

        libraries = self._runtime_library_map(extra_roots)
        elf_paths = list(self._iter_runtime_elfs(extra_roots))
        needed_by_elf = {
            elf_path: self._needed_entries(readelf, elf_path)
            for elf_path in elf_paths
        }

        created_absolute = 0
        created_relative = 0
        missing = []
        for entries in needed_by_elf.values():
            for needed in entries:
                if not self._is_conan_cache_needed_path(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                if self._link_needed_library(source, needed):
                    created_absolute += 1

        relative_bases = {os.path.abspath(root) for root in extra_roots if root}
        relative_bases.add(os.path.abspath(self.build_folder))
        # Upstream test executables run with cwd = their CMakeLists dir
        # (e.g. build/src/private/tests). Their DT_NEEDED entries like
        # "../../bin/libKDEGames6.so" resolve relative to that cwd, i.e. to
        # build/src/bin/. Provide compatibility links there as well.
        for rel in ("src", "tests", os.path.join("src", "private")):
            relative_bases.add(
                os.path.abspath(os.path.join(self.build_folder, rel, "bin"))
            )
        relative_bases.add(
            os.path.abspath(os.path.join(self.build_folder, os.pardir, "bin"))
        )
        for elf_path, entries in needed_by_elf.items():
            for needed in entries:
                if not self._is_relative_needed_path(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                targets = {
                    os.path.normpath(os.path.join(os.path.dirname(elf_path), needed))
                }
                targets.update(
                    os.path.normpath(os.path.join(base, needed))
                    for base in relative_bases
                )
                for target in targets:
                    if self._link_needed_library(source, target):
                        created_relative += 1

        if created_absolute or created_relative:
            self.output.info(
                "Prepared NEEDED compatibility links: "
                f"{created_absolute} absolute, {created_relative} relative"
            )
        if missing:
            self.output.warning(
                "Missing sources for NEEDED entries: "
                + ", ".join(sorted(set(missing))[:8])
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()
        self._sanitize_needed_entries()

    def package_info(self):
        # The project installs its own KDEGames6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6/KF6). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # Headers are installed as <prefix>/include/KDEGames6/KGameClock etc.,
        # so the default "include" dir alone would not resolve #include <KGameClock>
        # for non-CMake consumers (pkg_config/pkg-config/cmake_find_mode=none).
        self.cpp_info.includedirs = [
            os.path.join("include", "KDEGames6"),
            "include",
        ]
        self.cpp_info.libs = ["KDEGames6", "KDEGames6Private"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        # The QML module (org.kde.games.core) is installed under lib/qml, not
        # qml (verified in the package folder / install log), and this library
        # ships no Qt plugins.
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
