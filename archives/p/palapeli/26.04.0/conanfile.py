#!/usr/bin/env python3
"""Conan recipe for palapeli 26.04.0 on HarmonyOS PC (aarch64).

palapeli is the KDE Gear jigsaw-puzzle game: a KXmlGui/Qt Widgets
application (bin/palapeli), a shared library (libpala, the slicer plugin
API), three slicer plugin modules and a KIO thumbnail-creator plugin.

OHOS-specific adaptations (same family pattern as kjumpingcube 26.04.0,
kblocks 26.04.0 and libkdegames/26.04.0.1):
  - KF_IGNORE_PLATFORM_CHECK=TRUE -- OHOS is not in the KDE platform list
  - KF_SKIP_PO_PROCESSING=ON -- no gettext toolchain on the build image;
    ki18n_install(po) then stays a no-op instead of failing on msgfmt
  - KF6DocTools exists on ohpcd only as 6.19.0, while this graph is the
    uniform 6.18.0 closure (libkdegames/kiconthemes/knewstuff pin it). The
    6.19.0 recipe pulls karchive/6.19.0 + extra-cmake-modules/6.19.0 +
    libxslt/libxml2, i.e. a second KF6 line, and its KF6DocToolsConfig.cmake
    requires KF6Archive 6.19 -- adding it would tear the closure apart.
    The handbook pipeline (find_package component DocTools,
    add_subdirectory(doc), kdoctools_install(po)) is therefore patched out:
    the game has no runtime dependency on the handbook toolchain, so this
    is a documentation-only loss instead of a foreign version line.
  - kio has no 6.18.0 package on ohpcd (only 6.14.0 and 6.26.0), so kio is
    consumed at 6.14.0 and its KF6 6.14 requirement pins are overridden UP
    to the uniform 6.18.0 family: kio's installed configs request
    find_dependency(KF6* >= 6.14), which 6.18.0 satisfies, and KF6 keeps a
    stable ABI inside the major version (kjumpingcube precedent)
  - KF6DBusAddons (KDBusService in src/main.cpp) needs Qt6::DBus, which only
    the qtbase-sql-dbus/6.11.1 variant provides (knowledge E323/E441); its
    lib/cmake dir is prepended last in conan_cmakedeps_paths.cmake so that
    find_package(Qt6 ... DBus) can never resolve against the plain qtbase
    variant dragged in transitively
  - SharedMimeInfo is queried REQUIRED by mime/CMakeLists.txt; the mime
    integration (desktop mimetype registration + xdg-mime database update)
    is a desktop-session feature, so the subdirectory is adapted to make it
    optional on OHOS instead of pulling an extra host tool dependency
  - ECM_MODULE_PATH is set manually because the CMakeDeps-generated
    ECMConfig does not propagate the variable KF6 projects rely on
  - conan_cmakedeps_paths.cmake is written manually because qtbase/qtsvg and
    the KF6 packages use cmake_find_mode=none, which stops CMakeDeps from
    adding their lib/cmake dirs to CMAKE_PREFIX_PATH
  - package() retargets path-form DT_NEEDED entries (absolute conan-cache
    paths inherited from SONAME-less KF6 artifacts) to plain basenames and
    re-signs the rewritten ELF files (llvm-objcopy + binary-sign-tool);
    patchelf must not be used (knowledge E537)
  - upstream ships no test suite (no autotests/, no add_test/), so
    BUILD_TESTING=OFF and correctness is covered by test_package/ with real
    consumer checks (R51)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save


class PalapeliConan(ConanFile):
    name = "palapeli"
    version = "26.04.0"
    description = ("Palapeli - KDE Gear jigsaw puzzle game (KXmlGui "
                   "application with slicer plugin API and KIO thumbnailer)")
    license = "GPL-2.0-or-later"
    homepage = "https://apps.kde.org/palapeli"
    url = "https://invent.kde.org/games/palapeli"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::DBus (KF6DBusAddons/KDBusService in src/main.cpp) is only
        # provided by the qtbase-sql-dbus variant on ohpcd (E323/E441).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtsvg/6.11.1")
        # KIO is genuinely used: KF6::KIOWidgets in src/, KIOCore/KIOGui in
        # the thumbnail plugin. ohpcd publishes no kio/6.18.0.
        self.requires("kio/6.14.0")
        # Uniform KF6 6.18.0 closure for the whole graph. The overrides are
        # needed because kio/6.14.0 pins 6.14.0, while the newest
        # kiconthemes/6.18.0 recipe revision asks for karchive/6.19.0 and
        # knewstuff/6.18.0 (via libkdegames) asks for karchive/6.18.0.
        self.requires("karchive/6.18.0", override=True)
        self.requires("kauth/6.18.0", override=True)
        self.requires("kbookmarks/6.18.0", override=True)
        self.requires("kcolorscheme/6.18.0", override=True)
        self.requires("kcompletion/6.18.0", override=True)
        self.requires("kconfig/6.18.0", override=True)
        self.requires("kconfigwidgets/6.18.0", override=True)
        self.requires("kcoreaddons/6.18.0", override=True)
        self.requires("kcrash/6.18.0", override=True)
        self.requires("kguiaddons/6.18.0", override=True)
        self.requires("ki18n/6.18.0", override=True)
        self.requires("kiconthemes/6.18.0", override=True)
        self.requires("kitemviews/6.18.0", override=True)
        self.requires("kjobwidgets/6.18.0", override=True)
        self.requires("kservice/6.18.0", override=True)
        self.requires("kwidgetsaddons/6.18.0", override=True)
        self.requires("kwindowsystem/6.18.0", override=True)
        self.requires("solid/6.18.0", override=True)
        self.requires("kdbusaddons/6.18.0")
        self.requires("knotifications/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # Runtime closure of the KDEGames audio backend (libKDEGames6.so
        # DT_NEEDED libopenal.so.1 / libsndfile.so.1); declared explicitly so
        # the conan graph installs them for a pure consumer.
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")
        self.requires("libkdegames/26.04.0.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # mime/CMakeLists.txt queries find_package(SharedMimeInfo REQUIRED)
        # and calls update_xdg_mimetypes(); ECM's FindSharedMimeInfo only
        # needs the update-mime-database tool on PATH, and ohpcd publishes
        # shared-mime-info with a binary for this exact profile.
        self.tool_requires("shared-mime-info/2.5.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

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

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
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
        # Deterministic Qt6 resolution: the DBus-enabled variant is prepended
        # last so it ends up FIRST and find_package(Qt6 ... DBus) cannot hit
        # the plain qtbase variant dragged in transitively.
        qt_variant = self.dependencies.get("qtbase-sql-dbus")
        if qt_variant and qt_variant.package_folder:
            self._append_dependency_paths(lines, qt_variant.package_folder)
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

    def _build_runtime_env(self):
        # Host tools shipped by dependency packages (kconfig's
        # kconfig_compiler_kf6, qtbase's uic) link against conan Qt libraries
        # and are invoked directly by make with no loader path of their own.
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        return build_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._fix_exported_pala_config()
        self._sanitize_needed_entries()

    def _fix_exported_pala_config(self):
        # 上游导出的 PalaConfig.cmake 用的是非组件式写法
        #   find_dependency(Qt6Gui 6.5.0)
        # 它要求存在独立的 Qt6GuiConfig.cmake。Conan 侧 Qt6 由 CMakeDeps 以
        # Qt6::<Component> 形式提供（只有 Qt6Config.cmake），因此第三方按原样
        # find_package(Pala) 必然失败。改写为组件式依赖，导出包才真正可消费。
        cfg = os.path.join(self.package_folder, "lib", "cmake", "Pala", "PalaConfig.cmake")
        if not os.path.exists(cfg):
            return
        content = load(self, cfg)
        patched = content.replace("find_dependency(Qt6Gui 6.5.0)",
                                  "find_dependency(Qt6 6.5.0 COMPONENTS Gui)")
        if patched != content:
            save(self, cfg, patched)

    def _sanitize_needed_entries(self):
        # The KF6 6.18.0 artifacts carry no DT_SONAME, so the linker records
        # absolute conan-cache paths in DT_NEEDED and the artifact is not
        # portable (L5/E537). Retarget path-form entries to basenames, then
        # re-sign: OHOS refuses a rewritten ELF without a valid .codesign.
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        replaced = 0
        for rel in ("bin", "lib"):
            root = os.path.join(self.package_folder, rel)
            if not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in sorted(filenames):
                    path = os.path.join(dirpath, name)
                    if os.path.islink(path) or not os.path.isfile(path):
                        continue
                    if not self._is_elf(path):
                        continue
                    replaced += self._retarget_needed_in_place(path)
        if replaced:
            self.output.info(f"DT_NEEDED entries sanitized: {replaced}")

    @staticmethod
    def _elf_needed_basename_retarget(data):
        """In-place d_val retarget of path-form DT_NEEDED entries."""
        import struct

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
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 5:  # DT_STRTAB
                    strtab_addr = d_val
                    break
            if strtab_addr is None:
                continue
            strtab_off = None
            strtab_size = 0
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 in (3, 6, 7, 1):
                    strtab_off = sh_offset2
                    strtab_size = sh_size2
                    break
            if strtab_off is None:
                continue
            strtab = bytes(buf[strtab_off:strtab_off + strtab_size])
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag != 1:  # DT_NEEDED only
                    continue
                if d_val >= len(strtab):
                    continue
                end = strtab.find(b"\x00", d_val)
                if end < 0:
                    continue
                old = strtab[d_val:end]
                slash = old.rfind(b"/")
                if slash < 0:
                    continue  # already a plain basename
                base_off = d_val + slash + 1
                struct.pack_into("<Q", buf, pos + 8, base_off)
                replaced += 1
        return bytes(buf), replaced

    def _retarget_needed_in_place(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        patched, count = self._elf_needed_basename_retarget(data)
        if count:
            with open(path, "wb") as handle:
                handle.write(patched)
            self.output.info(
                f"NEEDED sanitized in {os.path.basename(path)}: {count}"
            )
            self._resign_elf(path)
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

    def package_info(self):
        # 本包自带上游导出的 CMake 配置（lib/cmake/Pala/PalaConfig.cmake），
        # 因此不生成 CMakeDeps 包装配置；但必须把 lib/cmake 登记为 builddir，
        # 否则消费者的 CMAKE_PREFIX_PATH 里没有它，find_package(Pala) 直接失败。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
