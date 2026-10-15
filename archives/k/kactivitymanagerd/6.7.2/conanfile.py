#!/usr/bin/env python3
"""Conan recipe for kactivitymanagerd 6.7.2 on HarmonyOS PC.

kactivitymanagerd is the KDE Plasma daemon that tracks user activities
(bin/kactivitymanagerd executable + KAMD plugins).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_DESIGNERPLUGIN=OFF: Qt Designer plugin requires Qt6UiPlugin, which
    is not published to ohpcd (qtbase does not ship it)
  - Dependencies: qtbase-sql-dbus/6.11.1 (superset qtbase build with
    FEATURE_dbus=ON and Sql; plain qtbase ships FEATURE_dbus=OFF and cannot
    satisfy find_package(Qt6 COMPONENTS DBus) — kglobalaccel 6.26.0
    precedent), boost/1.85.0 (header-only usage), kcoreaddons/6.26.0.1,
    kconfig/6.26.0, kdbusaddons/6.29.0, ki18n/6.26.0, kcrash/6.26.0,
    kglobalaccel/6.26.0, kxmlgui/6.26.0, kio/6.26.0,
    ecm/6.26.0 + qt6linguisttools/6.11.1 (tool_requires)
  - qt6linguisttools tool_require: ki18n_install(po) needs lrelease at
    build time (kglobalaccel 6.26.0 precedent)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
    (kcrash 6.26.0 precedent)
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH (kcrash 6.26.0 precedent)
  - /system/lib64 prepended to LD_LIBRARY_PATH: the sandbox
    LD_LIBRARY_PATH contains an incompatible libc++_shared.so which shadows
    the compatible one (kconfig 6.26.0 / bluez-qt 6.28.0 precedent); also
    needed because ECM's KDEInstallDirs runs the qtbase qtpaths host tool
    during configure
  - Upstream has no test suite (no autotests/ dir, no enable_testing() in
    any CMakeLists.txt); test_package runs the packaged daemon binary as
    smoke test
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


KDIRNOTIFY_XML = """\
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.kde.KDirNotify">
    <signal name="FilesAdded">
      <arg type="s" name="directory" direction="out"/>
    </signal>
    <signal name="FilesRemoved">
      <arg type="as" name="fileList" direction="out"/>
    </signal>
    <signal name="FilesChanged">
      <arg type="as" name="fileList" direction="out"/>
    </signal>
    <signal name="FileRenamed">
      <arg type="s" name="src" direction="out"/>
      <arg type="s" name="dst" direction="out"/>
    </signal>
    <signal name="FileRenamedWithLocalPath">
      <arg type="s" name="src" direction="out"/>
      <arg type="s" name="dst" direction="out"/>
      <arg type="s" name="dstPath" direction="out"/>
    </signal>
    <signal name="FileMoved">
      <arg type="s" name="src" direction="out"/>
      <arg type="s" name="dst" direction="out"/>
    </signal>
    <signal name="enteredDirectory">
      <arg type="s" name="url" direction="out"/>
    </signal>
    <signal name="leftDirectory">
      <arg type="s" name="url" direction="out"/>
    </signal>
  </interface>
</node>
"""


class KactivitymanagerdConan(ConanFile):
    name = "kactivitymanagerd"
    version = "6.7.2"
    description = "KDE Plasma activity manager daemon"
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://invent.kde.org/plasma/kactivitymanagerd"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core/DBus/Gui/Widgets/Sql are all provided by
        # qtbase-sql-dbus (superset build of qtbase with FEATURE_dbus=ON;
        # plain qtbase ships FEATURE_dbus=OFF — kglobalaccel 6.26.0
        # precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        # kdbusaddons/6.29.0 requires qtbase/6.11.1.1; qtbase-sql-dbus/6.11.1
        # links qtbase/6.11.1 — align on the newer patch version.
        self.requires("qtbase/6.11.1.1", override=True)
        self.requires("boost/1.85.0")
        self.requires("kcoreaddons/6.26.0.1", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("kconfig/6.26.0")
        self.requires("kdbusaddons/6.29.0")
        self.requires("kcrash/6.26.0")
        self.requires("kglobalaccel/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kio/6.26.0")
        # karchive/6.26.0 (transitive via kio) requires zlib/1.3.2; override
        # the zlib/1.3.1 that other deps pull in to avoid a version conflict.
        self.requires("zlib/1.3.2", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # ki18n_install(po) runs lrelease at build time (kglobalaccel
        # 6.26.0 precedent).
        self.tool_requires("qt6linguisttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Case-insensitive OHOS filesystem: libc++ __config's
        # #include <features.h> would resolve to src/service/Features.h.
        # Patch-based file renames/additions are not expressible, so the
        # rename and the vendored KDirNotify introspection XML are done
        # here instead (conandata patches only modify existing files).
        # Unconditional: self.settings is not accessible in source().
        if True:
            src = os.path.join(self.source_folder, "src", "service")
            os.rename(os.path.join(src, "Features.h"),
                      os.path.join(src, "FeaturesIface.h"))
            features_cpp = os.path.join(src, "Features.cpp")
            features_iface_cpp = os.path.join(src, "FeaturesIface.cpp")
            os.rename(features_cpp, features_iface_cpp)
            # keep the AUTOMOC include in sync with the renamed header
            with open(features_iface_cpp, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace('moc_Features.cpp',
                                      "moc_FeaturesIface.cpp")
            content = content.replace('#include "Features.h"',
                                      '#include "FeaturesIface.h"')
            with open(features_iface_cpp, "w", encoding="utf-8") as f:
                f.write(content)
            # kio's own D-Bus introspection XML for org.kde.KDirNotify
            # (LGPL-2.1-or-later, verbatim from kio 6.26.0), used by the
            # sqlite plugin's qt_add_dbus_interface (patch 0004).
            save(self, os.path.join(
                self.source_folder, "src", "service", "plugins", "sqlite",
                "org.kde.KDirNotify.xml"), KDIRNOTIFY_XML)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # CMake maps settings.os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, which
        # has no platform module; the generic fallback leaves the SONAME flag
        # undefined so shared libs get no DT_SONAME and executables record
        # the full relative build path as NEEDED (kglobalaccel 6.26.0
        # precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # Qt Designer plugin requires Qt6UiPlugin, which is not published to
        # ohpcd (qtbase does not ship it). Disable it explicitly.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # The project generates a D-Bus service file pointing at the daemon
        # and a systemd user unit; OHOS uses neither launcher, but installing
        # them is harmless and keeps the upstream install() intact.

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are
        # found (kcrash 6.26.0 precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase-sql-dbus uses cmake_find_mode=none -> CMakeDeps does not
            # generate conan_cmakedeps_paths.cmake. Create it manually so the
            # toolchain adds its cmake dirs to CMAKE_PREFIX_PATH/
            # CMAKE_MODULE_PATH (kglobalaccel 6.26.0 precedent).
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6*)
            # and transitive find_dependency() chains all resolve.
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            # qtbase-sql-dbus must win the find_package(Qt6) lookup: it is
            # the only provider of Qt6::DBus (plain qtbase ships
            # FEATURE_dbus=OFF) and also provides Core/Gui/Widgets/Sql
            # (kglobalaccel 6.26.0 precedent — prepend AFTER the dep loop so
            # it lands at the very front of the search path).
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
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
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # Sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so host
            # tools (qtpaths invoked by KDEInstallDirs during configure)
            # resolve the compatible libc++ first (kconfig 6.26.0 /
            # bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._relocatable_needed_sweep()
        self._bridge_dep_absolute_needed()
        self._sign_ohos_elfs()

    def _bridge_dep_absolute_needed(self):
        """Bridge registry binaries whose DT_NEEDED is a baked absolute path.

        Several published KF6 binaries (kcrash/6.26.0 -> libKF6CoreAddons.so;
        also seen with ki18n, kdbusaddons — E537 family) record their KF6
        dependencies as absolute paths under the Conan cache of the machine
        they were built on. Conan 2 cache folder names (p/<random>/) are
        per-install random, so those paths do not exist on any other
        machine. Loaders resolve DT_NEEDED entries containing "/" verbatim
        and never fall back to LD_LIBRARY_PATH, so any runtime use fails
        with "Error loading shared library ...".

        The published ELFs cannot be rewritten (patchelf-invalidated copies
        are refused by the OHOS loader signature check), so bridge instead:
        for every absolute NEEDED entry that does not exist, materialize a
        symlink at the baked path pointing at the real library of the same
        basename from the live dependency graph (fontconfig/DRAFT-E5xx
        precedent — the symlink leaves file contents untouched, signatures
        stay valid). Only missing paths inside the user's conan2 cache are
        materialized. Without this bridge the smoke test fails on any
        machine whose cache hash layout differs from the publishing machine.
        """
        def _tool(candidates):
            for c in candidates:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    return c
            return shutil.which(os.path.basename(candidates[-1]))

        if str(self.settings.os) != "OHOS":
            return
        readelf = _tool(["/data/service/hnp/bin/readelf", "readelf"])
        if not readelf:
            self.output.warning(
                "R05: readelf not found; skipping dep DT_NEEDED bridging"
            )
            return

        live_libs = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for entry in sorted(os.listdir(libdir)):
                if ".so" not in entry or entry in live_libs:
                    continue
                full = os.path.join(libdir, entry)
                if os.path.isfile(full):
                    live_libs[entry] = full

        bridged = 0
        scanned = set()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for entry in sorted(os.listdir(libdir)):
                elf_path = os.path.join(libdir, entry)
                if (".so" not in entry or not os.path.isfile(elf_path)
                        or os.path.islink(elf_path) or elf_path in scanned):
                    continue
                scanned.add(elf_path)
                try:
                    info = subprocess.run(
                        [readelf, "-d", elf_path], capture_output=True,
                        text=True, timeout=60,
                    ).stdout
                except Exception as exc:
                    self.output.warning(
                        "R05 readelf failed on {}: {}".format(elf_path, exc))
                    continue
                for line in info.splitlines():
                    if "(NEEDED)" not in line:
                        continue
                    needed = line.split("[", 1)[1].rsplit("]", 1)[0]
                    if (not os.path.isabs(needed) or os.path.exists(needed)
                            or ("/.conan2/" not in needed
                                and "/.cache/conan2/" not in needed)):
                        continue
                    source = live_libs.get(os.path.basename(needed))
                    if not source:
                        continue
                    try:
                        os.makedirs(os.path.dirname(needed), exist_ok=True)
                        os.symlink(source, needed)
                    except OSError as exc:
                        self.output.warning(
                            "R05: could not bridge {}: {}".format(
                                needed, exc))
                        continue
                    bridged += 1
                    self.output.info(
                        "R05 bridged: {} -> {}".format(needed, source))
        if bridged:
            self.output.info(
                "R05: bridged {} baked absolute DT_NEEDED path(s)".format(
                    bridged))

    def _sign_ohos_elfs(self):
        """Self-sign the packaged OHOS ELFs.

        The OHOS dynamic loader rejects unsigned ELF images with
        "Error loading shared library ..." even though the file exists in
        LD_LIBRARY_PATH (E452). Freshly built artifacts carry no .codesign
        section, so remove a stale one (if any) and self-sign every ELF
        under bin/ and lib/ (abbtr/1.0.4 precedent).
        """
        def _tool(candidates):
            for c in candidates:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    return c
            return shutil.which(os.path.basename(candidates[-1]))

        signer = _tool(["/data/service/hnp/bin/binary-sign-tool",
                        "binary-sign-tool"])
        objcopy = _tool(["/data/service/hnp/bin/llvm-objcopy",
                         "/data/service/hnp/bin/objcopy", "llvm-objcopy"])
        if not signer or not objcopy:
            self.output.warning(
                "R05: binary-sign-tool/llvm-objcopy not found "
                "(signer={}, objcopy={}); skipping OHOS ELF signing".format(
                    signer, objcopy)
            )
            return

        root = self.package_folder
        tmp_dir = os.path.join(root, ".sign-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            for subdir in ("bin", "lib"):
                base = os.path.join(root, subdir)
                if not os.path.isdir(base):
                    continue
                for dirpath, _dirnames, filenames in os.walk(base):
                    for fn in filenames:
                        p = os.path.join(dirpath, fn)
                        with open(p, "rb") as f:
                            magic = f.read(4)
                        if magic != b"\x7fELF":
                            continue
                        tmp_in = os.path.join(tmp_dir, fn)
                        tmp_out = tmp_in + ".signed"
                        shutil.copy2(p, tmp_in)
                        subprocess.run(
                            [objcopy, "--remove-section", ".codesign",
                             tmp_in],
                            capture_output=True, timeout=60,
                        )
                        subprocess.run(
                            [signer, "sign", "-selfSign", "1",
                             "-inFile", tmp_in, "-outFile", tmp_out,
                             "-signAlg", "SHA256withECDSA"],
                            check=True, capture_output=True, text=True,
                            timeout=60,
                        )
                        os.chmod(tmp_out, 0o755)
                        shutil.move(tmp_out, p)
                        os.chmod(p, 0o755)
                        self.output.info("R05 signed: {}".format(
                            os.path.relpath(p, root)))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _relocatable_needed_sweep(self):
        """Rewrite absolute-path DT_NEEDED entries to plain basenames.

        Several published KF6 dependencies (kdbusaddons/6.29.0,
        ki18n/6.26.0, kcrash/6.26.0) ship .so files without DT_SONAME, so
        the linker records the absolute Conan cache path in our artifacts'
        DT_NEEDED (L5b soname gate). The runtime resolves plain basenames
        through LD_LIBRARY_PATH, so rewriting them is safe
        (alkimia/8.2.1 precedent).
        """
        def _tool(candidates):
            for c in candidates:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    return c
            return shutil.which(os.path.basename(candidates[-1]))

        readelf = _tool(["/data/service/hnp/bin/readelf", "readelf"])
        patchelf = _tool(["/data/service/hnp/bin/patchelf", "patchelf"])
        if not readelf or not patchelf:
            self.output.warning(
                "R05: readelf/patchelf not found (readelf={}, patchelf={}); "
                "skipping relocatable NEEDED sweep".format(readelf, patchelf)
            )
            return

        root = self.package_folder
        for subdir in ("bin", "lib"):
            base = os.path.join(root, subdir)
            if not os.path.isdir(base):
                continue
            for dirpath, _dirnames, filenames in os.walk(base):
                for fn in filenames:
                    p = os.path.join(dirpath, fn)
                    if not os.path.isfile(p) or os.path.islink(p):
                        continue
                    try:
                        info = subprocess.run(
                            [readelf, "-d", p], capture_output=True,
                            text=True, timeout=60
                        ).stdout
                    except Exception as exc:
                        self.output.warning(
                            "readelf failed on {}: {}".format(p, exc))
                        continue
                    for line in info.splitlines():
                        if "(NEEDED)" not in line:
                            continue
                        entry = line.split("[", 1)[1].rsplit("]", 1)[0]
                        if not entry.startswith(("/", "../")):
                            continue
                        basename = os.path.basename(entry)
                        try:
                            subprocess.run(
                                [patchelf, "--replace-needed", entry,
                                 basename, p],
                                check=True, capture_output=True, text=True,
                                timeout=60,
                            )
                            self.output.info(
                                "R05 relocatable: {} -> {} in {}".format(
                                    entry, basename, p)
                            )
                        except subprocess.CalledProcessError as exc:
                            self.output.warning(
                                "R05 patchelf failed on {} ({}): {}".format(
                                    p, entry, exc.stderr.strip())
                            )

    def package_info(self):
        # Application package: the daemon binary and KAMD plugins.
        # cmake installs the daemon to bin/ (KDEInstallDirs Linux layout on
        # OHOS, no libexec suffix override)
        self.cpp_info.bindirs = ["bin"]
        # The project installs its own plugin metadata under
        # <plugins>/kactivitymanagerd1/. Keep cpp_info minimal; consumers
        # use the daemon through D-Bus, not CMake.
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
