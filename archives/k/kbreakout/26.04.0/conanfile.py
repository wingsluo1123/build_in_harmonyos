#!/usr/bin/env python3
"""Conan recipe for kbreakout 26.04.0 on HarmonyOS PC (aarch64).

kbreakout is the KDE Gear Breakout game (KBreakOut): a Qt6/KF6 application
whose board is rendered by a QML scene shipped in src/qml/*.qml and driven
by a QQuickWidget (src/canvaswidget.cpp), on top of the KDEGames6 library
(libkdegames 26.04.0.1, published on the ohpcd registry). Upstream ships one
GUI executable: bin/kbreakout.

Upstream test suite: none (R51 inventory). The 26.04.0 release tarball has
no tests/, autotests/ or test/ directory and no enable_testing()/add_test()/
ecm_add_test(s)() call in any CMakeLists.txt - upstream QA runs through KDE
CI source builds. Consumer-side verification is therefore provided by
test_package (kfourinline 26.04.0 precedent).

OHOS-specific adaptations (patches/):
  - 0001-ohos-skip-kdoctools.patch: KF6 DocTools removed from the REQUIRED
    component list and the doc/ handbook + kdoctools_install(po) steps
    dropped - kdoctools is not part of the published KF6 6.18/6.26 closure
    and the DocBook handbook is not a runtime requirement for the game
    (kblocks 26.04.0 / kfourinline 26.04.0 precedent).
  - 0002-canvaswidget-cpp-use-KLocalizedContext.patch: upstream uses
    KLocalizedQmlContext (KF6::I18nQml) for KI18N >= 6.8, but the published
    ki18n 6.18.0 package ships only the core KF6I18n library (no
    KF6I18nQml module, no KLocalizedQmlContext header). The patch switches
    the QQuickWidget engine context to the equivalent KLocalizedContext
    from KF6::I18n and keeps it visible with
    KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0 (alligator 26.04.0 precedent;
    the QML-side i18n()/xi18n() API surface is unchanged).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext toolchain; catalogs are not needed for
    the smoke-verified deliverable).
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1 (Qt6
    Core/Gui/Widgets/Network/Xml), qtdeclarative 6.11.1 (Qt6 Qml/Quick/
    QuickWidgets for the QML board), qtsvg 6.11.1 (Qt6::Svg, used by the
    KDEGames SVGZ theme renderer), KF6 6.18.0 framework set + kdnssd
    6.29.0, libkdegames 26.04.0.1 (KDEGames6 + KDEGames6Private + the
    org.kde.games.core QML module imported by src/qml/*.qml), ecm 6.26.0
    (tool_requires).
  - karchive/6.18.0 pinned with override=True (libkdegames 26.04.0.1 graph
    precedent: the newest kiconthemes/6.18.0 recipe revision requires
    karchive/6.19.0, which conflicts with knewstuff/6.18.0).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - -Wl,-z,max-page-size=0x1000 pinned for the executable: the OHOS musl
    loader refuses the lld default 0x10000 layout when the dynamic section
    is split into high-address RW LOAD segments (DRAFT-3888 audiocd
    precedent); the flag is appended to CMAKE_EXE_LINKER_FLAGS because a
    non-empty value assigned in the toolchain makes CMake skip the
    CMAKE_EXE_LINKER_FLAGS_INIT initialization.
  - 7Zip stays optional and absent (libkdegames 26.04.0 precedent): the
    theme SVGZ generation in cmake/InternalMacros.cmake falls back to
    "gzip -9 -n -c".
  - package(): path-form DT_NEEDED entries are rewritten to plain basenames
    in place (.dynstr content only, same length -> dynamic section offsets
    unchanged), then the ELF is re-signed. The published KF6 6.18.0
    artifacts carry no DT_SONAME, so the linker records this package's
    link-time conan-cache paths as DT_NEEDED and the artifact would not be
    consumable outside the build machine (E537 Conan cache absolute
    DT_NEEDED leakage / DRAFT-14403 normalize + re-sign). The 4K page size
    keeps .dynsym/.dynstr in a single LOAD so the in-place patch is safe.
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
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KbreakoutConan(ConanFile):
    name = "kbreakout"
    version = "26.04.0"
    description = (
        "KDE Breakout game (KBreakOut) - a Qt6/KF6 QML-rendered application "
        "built on the KDEGames6 library"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/games/kbreakout"
    url = "https://invent.kde.org/games/kbreakout"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        # kdnssd is not in kbreakout's own find_package(KF6 COMPONENTS ...)
        # list, but it is a runtime DT_NEEDED of the published libKDEGames6
        # (LAN discovery / highscore infrastructure) and therefore part of
        # the closure this recipe pins (kblocks 26.04.0 precedent).
        self.requires("kdnssd/6.29.0")
        self.requires("ki18n/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("libkdegames/26.04.0.1")
        # karchive: force the 6.18.0 line for the whole graph (libkdegames
        # 26.04.0.1 precedent: the newest kiconthemes/6.18.0 recipe revision
        # requires karchive/6.19.0, which conflicts with knewstuff/6.18.0
        # (karchive/6.18.0)). The override pins the compatible 6.18.0 so the
        # KF6 6.18 closure stays consistent.
        self.requires("karchive/6.18.0", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream registers no test suite (see module docstring).
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        exe_ldflags = "-Wl,--disable-new-dtags"
        if self.settings.os == "OHOS":
            exe_ldflags += " -Wl,-z,max-page-size=0x1000"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = exe_ldflags

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt6 split-package component discovery: Qt6Svg lives in qtsvg and
        # Qt6 Qml/Quick/QuickWidgets live in qtdeclarative (libkdegames
        # verified pattern).
        qt_extra = []
        for dep_name in ("qtsvg", "qtdeclarative"):
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
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc/uic/rcc/kconfig_compiler) shipped by the conan
        # packages are OHOS binaries: they need the compatible libc++_shared
        # from /system/lib64 plus the dependency lib dirs on LD_LIBRARY_PATH
        # (kblocks 26.04.0 / kfourinline 26.04.0 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                build_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        if self.settings.os == "OHOS":
            # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Resolve the signing tools first: a DT_NEEDED rewrite invalidates
            # .codesign, so the package must never be left unpatched-and-
            # unsigned (or patched-and-unsigned) on the device.
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

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

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
        # Application package: one executable in bin/, no library deliverable
        # (kbreakout links KDEGames6 and the KF6/Qt6 runtime).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Runtime env for consumers: the game needs the KDEGames6/Qt6/KF6
        # libraries, the KDEGames6 QML module (org.kde.games.core) and its own
        # share/kbreakout data tree (qml/, themes/, levelsets/, sounds/).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
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
                self.runenv_info.prepend_path(
                    "XDG_DATA_DIRS", os.path.join(dep.package_folder, "share")
                )
