#!/usr/bin/env python3
"""Conan recipe for kmines 26.04.0 on HarmonyOS PC (aarch64).

KMines is the classic KDE minesweeper game: a Qt6/KF6 QGraphicsView
application built on the KDEGames6 library (libkdegames 26.04.0.1,
published on the ohpcd registry). Upstream ships one GUI executable
(kmines), six SVGZ-compressed game themes (default, classic, green,
graveyard-mayhem, clean_blue, clean_blue_dark) plus the desktop file,
appdata metadata and hicolor icons.

OHOS-specific adaptations (no source patches required):
  - KF6 DocTools is OPTIONAL upstream (find_package(KF6DocTools) without
    REQUIRED, and both doc/ and kdoctools_install(po) sit behind
    if(KF6DocTools_FOUND)), so the handbook is skipped automatically when
    the component is absent from the published KF6 closure. Unlike
    kfourinline/kgoldrunner no patch is needed.
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext msgfmt toolchain; catalogs are not
    needed for the smoke-verified deliverable).
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1 (Qt6
    Core/Gui/Widgets/Network/Xml), qtsvg 6.11.1 (Qt6::Svg), the KF6 6.18.0
    framework set (incl. ktextwidgets for KF6::TextWidgets) + kdnssd
    6.29.0, libkdegames 26.04.0.1 (KDEGames6 + KDEGames6Private; the
    .1 revision carries the SONAME/DT_NEEDED fixes), ecm 6.26.0
    (tool_requires).
  - karchive/6.18.0 pinned with override=True and kiconthemes switched to
    the published 6.18.0.1 fix release with override=True (kmousetool
    26.04.0 precedent: the newest kiconthemes/6.18.0 recipe revision
    requires karchive/6.19.0, which conflicts with knewstuff/6.18.0, and
    has no 6.18.0-line binary on the registry; 6.18.0.1 is that same
    recipe rebuilt against karchive/6.18.0).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on;
    the ECM FindKF6.cmake umbrella module then dispatches the
    find_package(KF6 COMPONENTS ...) call to the individual KF6Xxx
    configs.
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - 7Zip stays optional and absent (same as libkdegames): theme SVGZ
    generation uses the gzip -9 -n -c fallback (toybox gzip on OHOS
    handles the flags).
  - Upstream registers no test suite (no tests/, autotests/ or add_test()
    anywhere in the tarball; N=0). Consumer-side verification is provided
    by test_package (installed binary --version execution, offscreen GUI
    boot, KGameThemeProvider theme discovery of the six installed themes,
    and a KGameRenderer sprite render through the SVGZ theme pipeline).
"""
import glob
import os
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)


class KminesConan(ConanFile):
    name = "kmines"
    version = "26.04.0"
    description = (
        "KDE minesweeper game (KMines) - Qt6/KF6 QGraphicsView application "
        "with six SVGZ game themes, built on KDEGames6/libkdegames"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/games/kmines"
    url = "https://invent.kde.org/games/kmines"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("kdnssd/6.29.0")
        self.requires("ki18n/6.18.0")
        # KF6::TextWidgets (KMines main window code editor widgets)
        self.requires("ktextwidgets/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # kiconthemes/6.18.0.1: the published 6.18.0 recipe revision now
        # requires karchive/6.19.0 (no 6.18.0-line binary on the registry);
        # 6.18.0.1 is the same recipe rebuilt against karchive/6.18.0 and
        # has a matching binary (kmousetool 26.04.0 precedent).
        self.requires("kiconthemes/6.18.0.1", override=True)
        self.requires("libkdegames/26.04.0.1")
        # karchive: force the 6.18.0 line for the whole graph (libkdegames
        # 26.04.0 graph precedent: the newest kiconthemes/6.18.0 recipe
        # revision requires karchive/6.19.0, which conflicts with
        # knewstuff/6.18.0 (karchive/6.18.0)). The override pins the
        # compatible 6.18.0 so the KF6 6.18 closure stays consistent.
        self.requires("karchive/6.18.0", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        # Standard patch plumbing: conandata.yml carries no patches for this
        # port (0 platform patches), so this exports an empty set. Keeping
        # the hook makes the recipe ready for a future patch series.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing needs the gettext msgfmt toolchain; skip it
        # (khealthcertificate 26.04.3 / audiocd 26.04.3 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # OHOS loader workaround (audiocd 26.04.3 precedent): default lld
        # 0x10000 max-page-size can split .dynsym/.dynstr into separate
        # high-address RW LOAD segments which the OHOS musl loader refuses
        # to mmap; pin the 4K page layout.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt6 split-package component discovery: Qt6Svg lives in the qtsvg
        # package (libkdegames verified pattern).
        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6/libkdegames packages use cmake_find_mode=none, so
        # CMakeDeps doesn't put their lib/cmake dirs on CMAKE_PREFIX_PATH.
        # Write conan_cmakedeps_paths.cmake manually (libkdegames precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
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

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        # No-op for this port (conandata.yml has no patches), kept as the
        # house-standard hook ahead of configure.
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc/uic/rcc/kconfig_compiler) shipped by the conan
        # packages are OHOS binaries: they need the compatible
        # libc++_shared from /system/lib64 plus the dependency lib dirs on
        # LD_LIBRARY_PATH (audiocd 26.04.3 / kconfig 6.26.0 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Resolve the signing tools first: a DT_NEEDED rewrite invalidates
            # .codesign, so the package must never be left unpatched-and-
            # unsigned (kbreakout 26.04.0 / kapptemplate 26.04.0 E077
            # precedent: the OHOS loader refuses to execute an unsigned ELF).
            objcopy, signer = self._ohos_sign_tools()
            patched = self._normalize_needed_paths()
            self._sign_ohos_elf_tree(self.package_folder, objcopy, signer)
            if patched:
                self.output.info(
                    f"DT_NEEDED paths normalized in {patched} package file(s)"
                )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _normalize_needed_paths(self):
        """Rewrite path-form DT_NEEDED strings to plain basenames in place.

        The published KF6 6.18.0 dependency artifacts carry no DT_SONAME
        (Platform/HarmonyOS gap), so the linker records the link-time
        conan-cache absolute path of every such dependency in this package's
        DT_NEEDED. Those paths do not exist on a consumer machine with a
        different cache layout, so the artifact would not be loadable
        (E537). The rewrite changes .dynstr content only and keeps the
        string length, so the dynamic section offsets stay valid; the caller
        re-signs the ELF afterwards.
        """
        patched = 0
        for rel in ("bin", "lib"):
            folder = os.path.join(self.package_folder, rel)
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                path = os.path.join(folder, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                with open(path, "rb") as handle:
                    data = handle.read()
                new_data, count = self._elf_needed_basenames(data)
                if not count:
                    continue
                with open(path, "wb") as handle:
                    handle.write(new_data)
                self.output.info(f"normalized {count} DT_NEEDED path(s) in {name}")
                patched += 1
        return patched

    @staticmethod
    def _elf_needed_basenames(data):
        """Return (data', replaced) with path-form DT_NEEDED strings reduced
        to their basename. ELF64 little-endian only; every other input is
        returned untouched."""
        if len(data) < 64 or data[:4] != b"\x7fELF":
            return data, 0
        if data[4] != 2 or data[5] != 1:
            return data, 0
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0 or e_shnum == 0:
            return data, 0

        sections = []
        for index in range(e_shnum):
            off = e_shoff + index * e_shentsize
            if off + e_shentsize > len(data):
                break
            sections.append(
                (
                    struct.unpack_from("<I", data, off + 4)[0],   # sh_type
                    struct.unpack_from("<Q", data, off + 16)[0],  # sh_addr
                    struct.unpack_from("<Q", data, off + 24)[0],  # sh_offset
                    struct.unpack_from("<Q", data, off + 32)[0],  # sh_size
                )
            )

        buf = bytearray(data)
        replaced = 0
        for sh_type, _sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or sh_size == 0:  # SHT_DYNAMIC
                continue
            if sh_offset + sh_size > len(data):
                continue
            strtab_addr = None
            strtab_size = None
            needed_offsets = []
            used_offsets = set()
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                if pos + 16 > len(data):
                    break
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:
                    break
                if d_tag == 5:  # DT_STRTAB
                    strtab_addr = d_val
                elif d_tag == 10:  # DT_STRSZ
                    strtab_size = d_val
                elif d_tag == 1:  # DT_NEEDED
                    needed_offsets.append(d_val)
                    used_offsets.add(d_val)
                elif d_tag in (14, 15, 29) and d_val:  # SONAME/RPATH/RUNPATH
                    used_offsets.add(d_val)
            if strtab_addr is None or not needed_offsets:
                continue
            strtab_off = None
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 == 3 and sh_size2:
                    strtab_off = sh_offset2
                    if strtab_size is None or strtab_size > sh_size2:
                        strtab_size = sh_size2
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
                if not base:
                    continue
                # Never clobber a string another dynamic entry also points at.
                if any(off < used < end for used in used_offsets):
                    continue
                buf[strtab_off + off:strtab_off + end] = (
                    base + b"\x00" * (len(old) - len(base))
                )
                replaced += 1
        return bytes(buf), replaced

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

    def _ohos_sign_tools(self):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS ELF signing tools not found (llvm-objcopy / "
                "binary-sign-tool); the packaged executable must be signed "
                "to run on the device"
            )
        return objcopy, signer

    def _sign_ohos_elf_tree(self, root_folder, objcopy, signer):
        signed = 0
        for root, _dirs, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self._resign(path, objcopy, signer)
                signed += 1
        self.output.info(f"signed {signed} OHOS ELF file(s)")

    def _resign(self, path, objcopy, signer):
        mode = os.stat(path).st_mode & 0o777
        probe = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            self.output.warning(
                "llvm-objcopy --remove-section .codesign failed: "
                f"{probe.stderr.strip()[:120]}"
            )
        probe = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            raise ConanException(
                f"binary-sign-tool sign failed for {path}: "
                f"{probe.stderr.strip()[:200]}"
            )
        os.chmod(path, mode)

    def package_info(self):
        # Application package: one executable in bin/, no library
        # deliverable (kmines links KDEGames6 at runtime).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Runtime env for consumers: the game needs KDEGames6/Qt6/KF6 libs
        # plus the QML import path of KDEGames6 (reflection scene plugin).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
