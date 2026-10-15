#!/usr/bin/env python3
"""Conan recipe for kcolorchooser 26.04.0 on HarmonyOS PC (aarch64).

kcolorchooser is the KDE Gear colour chooser / palette tool: a single Qt6
Widgets executable (bin/kcolorchooser) that wraps QColorDialog and adds the
KDE clipboard / ``--print`` / ``--color`` command-line interface. Upstream
(KDE release-service 26.04.0, invent.kde.org/graphics/kcolorchooser) requires
only Qt6 (Core/Gui/Widgets) plus the KF6 components CoreAddons (KAboutData),
I18n (KLocalizedString) and XmlGui (KHelpMenu).

Upstream tests (R51 step 1 inventory, evidence):
  - the 26.04.0 tarball ships **no** autotests/ directory and no tests/
    directory;
  - CMakeLists.txt registers no test at all: no ``add_test``/``enable_testing``
    /``BUILD_TESTING``/``ecm_add_test`` usage, the only target being
    ``add_executable(kcolorchooser)`` + ``target_sources(kcolorchooser PRIVATE
    kcolorchooser.cpp)``;
  - the upstream CI configuration defines no test suite for the project:
    .gitlab-ci.yml includes nine shared KDE CI templates (linux-qt6,
    linux-qt6-next, freebsd-qt6, windows-qt6, flatpak, snap-snapcraft-lxd and
    the clang-format/xml-lint/yaml-lint lint jobs) — those templates build,
    package and lint, and would run ctest only if the project registered
    tests, which it does not; .kde-ci.yml carries only dependency metadata
    plus ``require-passing-tests-on`` and declares no test target;
  - therefore the upstream suite is 0 tests, declared as such in
    test_package/MANIFEST.yml (``upstream_tests: []``, ``assertion_count``
    covers the consumer cases only).

Licensing note: upstream COPYING and org.kde.kcolorchooser.appdata.xml
(<project_license>MIT</project_license>) state **MIT**, which is what the
Conan ``license`` field records. However kcolorchooser.cpp:51 passes
``KAboutLicense::BSD_2_Clause`` to KAboutData, so the shipped binary's
``--license`` output prints the BSD-2-Clause text; the consumer case asserts
that runtime output (it verifies the KAboutData metadata path), not the SPDX
identifier of the recipe.

OHOS-specific adaptations (all configuration-level, no upstream source patch
is needed for this package — conandata.yml carries no patches):
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in KDE's platform list.
  - KF_SKIP_PO_PROCESSING=ON: ``ki18n_install(po)`` would need the gettext
    msgfmt/lconvert toolchain, which is unavailable on this platform; the
    .qm catalogs are not required for the smoke-verified deliverable
    (kteatime/kblocks 26.04.0 precedent).
  - BUILD_TESTING=OFF: upstream registers no tests (see above); the consumer
    verification lives in test_package/ instead.
  - ECM_MODULE_PATH is set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable that the project's
    CMakeLists.txt (and KDEInstallDirs/KDECMakeSettings) relies on.
  - conan_cmakedeps_paths.cmake is written manually because qtbase and the
    KF6 packages use cmake_find_mode=none, which prevents CMakeDeps from
    adding their lib/cmake directories to CMAKE_PREFIX_PATH.
  - CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH point at every dependency lib
    directory and -Wl,--disable-new-dtags keeps them as DT_RPATH: the OHOS
    loader otherwise falls through to the broken RPATH entries baked into the
    published KF6 libraries (kteatime 26.04.0 precedent).
  - -Wl,-z,max-page-size=0x1000: the OHOS musl loader rejects the default
    lld 0x10000 multi-RW-LOAD layout (kblocks 26.04.0 precedent).
  - DT_NEEDED entries of the shipped executable are sanitized in package():
    the published KF6 6.18.0 artifacts carry no DT_SONAME, so the linker
    records absolute conan-cache paths in DT_NEEDED. They are rewritten to
    plain basenames via an in-place .dynstr patch, then the ELF is re-signed
    with llvm-objcopy --remove-section .codesign + binary-sign-tool (OHOS
    requires a valid .codesign). The rewritten names resolve through the
    DT_RPATH installed above and through the exported runenv_info.
"""
import os
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KColorChooserConan(ConanFile):
    name = "kcolorchooser"
    version = "26.04.0"
    description = (
        "KDE colour chooser and palette tool (KColorChooser) - a Qt6/KF6 "
        "Widgets application built on KF6 CoreAddons/I18n/XmlGui"
    )
    license = "MIT"
    homepage = "https://invent.kde.org/graphics/kcolorchooser"
    url = "https://invent.kde.org/graphics/kcolorchooser"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Upstream REQUIRED KF6 set: CoreAddons, I18n, XmlGui. The remaining
        # entries are the runtime DT_NEEDED closure of that set (kxmlgui pulls
        # kconfig/kconfigwidgets/kguiaddons/kiconthemes/kitemviews/
        # kwidgetsaddons/kcolorscheme); they are declared explicitly so the
        # consumer graph and runenv are complete (kteatime 26.04.0 precedent).
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream registers no tests (0 tests, see module docstring).
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

        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000 -Wl,--disable-new-dtags"
            )

        # DT_RPATH (not DT_RUNPATH) pointing at every dependency lib dir: the
        # OHOS loader reaches the published KF6 libraries through it before
        # their own broken RPATH entries are considered (kteatime precedent).
        dep_lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib"))
        ]
        if dep_lib_dirs:
            rpath = os.pathsep.join(dep_lib_dirs)
            tc.variables["CMAKE_BUILD_RPATH"] = rpath
            tc.variables["CMAKE_INSTALL_RPATH"] = rpath

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        """CMakeDeps cannot add cmake_find_mode=none packages to
        CMAKE_PREFIX_PATH, so the dependency search paths are written by hand
        (kblocks/kteatime 26.04.0 precedent)."""
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
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships no test suite for kcolorchooser 26.04.0 (0 tests,
        # evidence in the module docstring and test_package/MANIFEST.yml), so
        # there is no ctest invocation here; the consumer verification runs in
        # test_package/ during conan create.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sanitize_needed_entries()

    def _sanitize_needed_entries(self):
        """Rewrite path-form DT_NEEDED entries to plain basenames (in-place
        .dynstr patch), then re-sign the ELF (OHOS requires valid .codesign).

        The published KF6 6.18.0 artifacts carry no DT_SONAME, so bin/
        kcolorchooser records the absolute conan-cache paths of libKF6*.so in
        DT_NEEDED. Such an artifact is not portable (loader error outside the
        build machine). Plain basenames resolve through the installed
        DT_RPATH and the exported runenv LD_LIBRARY_PATH instead.
        """
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        replaced = 0
        for subdir in ("bin", "lib"):
            directory = os.path.join(self.package_folder, subdir)
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                if not os.path.isfile(path):
                    continue
                if not (name.endswith(".so") or ".so." in name or subdir == "bin"):
                    continue
                if not self._is_elf(path):
                    continue
                replaced += self._patch_needed_paths_in_place(path)
        if replaced:
            self.output.info(f"DT_NEEDED entries sanitized: {replaced}")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _patch_needed_paths_in_place(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        patched, count = self._elf_dynstr_patch(data)
        if count:
            with open(path, "wb") as handle:
                handle.write(patched)
            self.output.info(
                f"NEEDED sanitized in {os.path.basename(path)}: {count}"
            )
            self._resign_elf(path)
        return count

    @staticmethod
    def _elf_dynstr_patch(data):
        if data[:4] != b"\x7fELF":
            return data, 0
        ei_class = data[4]
        ei_data = data[5]
        if ei_class != 2 or ei_data != 1:
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
            if sh_type != 6 or sh_size == 0:
                continue
            strtab_addr = None
            strtab_size = None
            needed_offsets = []
            used_offsets = set()
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:
                    break
                if d_tag == 5:
                    strtab_addr = d_val
                elif d_tag == 10:
                    strtab_size = d_val
                elif d_tag in (1, 14, 15, 29):
                    needed_offsets.append(d_val)
                    used_offsets.add(d_val)
                elif 0 < d_val < 0x100000:
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
                if any(off < u < end for u in used_offsets):
                    continue
                new = base + b"\x00" * (len(old) - len(base))
                buf[strtab_off + off:strtab_off + end] = new
                replaced += 1
        return bytes(buf), replaced

    def _resign_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                f"llvm-objcopy/binary-sign-tool not found; "
                f"{path} stays without a fresh signature"
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
                f"llvm-objcopy --remove-section .codesign failed: "
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
                f"binary-sign-tool sign failed: {probe.stderr.strip()[:120]}"
            )
            return False
        shutil.move(signed, path)
        os.chmod(path, mode)
        return True

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

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
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
