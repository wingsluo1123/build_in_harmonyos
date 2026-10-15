#!/usr/bin/env python3
"""Conan recipe for kaccounts-integration 26.04.0 on HarmonyOS PC.

KAccounts — KDE online-accounts integration library (libkaccounts + KCM +
kded module + QML plugin + kio-webdav provider plugin), released as part of
KDE Release Service 26.04.0.

OHOS-specific adaptations (26.04.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: msgfmt-based po install is skipped (the
    translation domain is not functional on OHOS; gettext msgfmt is only
    needed for ki18n_install which we intentionally bypass)
  - BUILD_TESTING=OFF: upstream ships no tests/ or autotests/ directory
    (verified against the 26.04.0 release tarball)
  - Qt6 Qml comes from the published qtdeclarative/6.11.1 package, wired in
    through QT_ADDITIONAL_PACKAGES_PREFIX_PATH (kdeclarative/kcmutils 6.26.0
    precedent); its qtbase/6.11.1 pin is overridden to qtbase/6.11.1.1 (the
    OHOS adaptation-fix line the rest of the accounts-sso/KF6 stack uses).
  - AccountsQt6/libaccounts-qt 1.17 and SignOnQt6/libsignon-qt 8.61 are the
    OHOS Qt6-flavour packages of this repo; QCoro6/qcoro 0.13.0 provides
    QCoro::Core for the kio-webdav plugin.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KAccountsIntegrationConan(ConanFile):
    name = "kaccounts-integration"
    version = "26.04.0"
    description = "KDE KAccounts — online accounts integration (library, KCM, kded module)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/network/kaccounts-integration"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus is not needed here: plain qtbase carries
        # Core/Gui/Widgets/Xml (kconfig 6.26.0 precedent); DBus support the
        # kded module needs arrives via KF6DBusAddons/kdbusaddons.
        self.requires("qtbase/6.11.1.1", override=True)
        # Qt6::Qml for the declarative plugin (qtbase package has no Qml).
        self.requires("qtdeclarative/6.11.1")
        # KF6 6.26 line; override=True entries pin the whole graph
        # (kcmutils/kxmlgui 6.26.0 precedent) so the 6.18-line pins of
        # kwallet/kio collapse onto the 6.26 line.
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kservice/6.26.0", override=True)
        self.requires("karchive/6.26.0", override=True)
        self.requires("kitemviews/6.26.0", override=True)
        self.requires("kcmutils/6.26.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("kwallet/6.18.0")
        self.requires("kio/6.26.0")
        # accounts-sso Qt6 stack + QCoro (all published on ohpcd).
        self.requires("libaccounts-qt/1.17")
        self.requires("libsignon-qt/8.61")
        self.requires("qcoro/0.13.0")
        # kio -> karchive/kservice chain: KF6ArchiveConfig activates
        # find_dependency(OpenSSL)/PkgConfig::LibZstd; libxml2 is needed by
        # the OHOS SDK lld at link time (kio 6.26.0 precedent).
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxml2/2.15.3")
        # libaccounts-qt -> glib2 pins zlib/1.3.1; kio 6.26.0 line pins
        # zlib/1.3.2 — collapse onto the newer published line.
        self.requires("zlib/1.3.2", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        deps = CMakeDeps(self)
        # qtbase on ohpcd ships Qt's own Qt6Config.cmake (cmake_find_mode=none);
        # map its conan name onto the real config so the transitive
        # find_dependency() calls emitted by AccountsQt6/SignOnQt6/QCoro6
        # configs resolve (libaccounts-qt 1.17 test_package precedent).
        deps.set_property("qtbase", "cmake_file_name", "Qt6")
        # Packages that depend on the qtbase *global* target record refs like
        # "qtbase::qtbase" (qcoro 0.13.0 Core component); map them onto the
        # real Qt6::Core so the interface resolves.
        deps.set_property("qtbase", "cmake_target_name", "Qt6::Core")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # CMake ships no Platform/HarmonyOS module, so CMAKE_SHARED_LIBRARY_SONAME_*
        # stays empty and lld emits no DT_SONAME for libkaccounts6.so. Consumers
        # then record the absolute build-machine cache path in DT_NEEDED and fail
        # to load on clean machines. Provide the flags so every shared lib built
        # here gets a DT_SONAME (kcoreaddons/kio 6.26.0 precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        # Qt6Qml lives in the qtdeclarative package; Qt discovers additional
        # components through the official QT_ADDITIONAL_PACKAGES_PREFIX_PATH
        # hook (kdeclarative 6.26.0 precedent). Without it find_package(Qt6
        # ... Qml) resolves the qtbase Qt6Config.cmake first and fails on the
        # missing component.
        qt_extra = []
        qtdecl = self.dependencies.get("qtdeclarative")
        if qtdecl and qtdecl.package_folder:
            qt_extra.append(qtdecl.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        self._write_cmake_paths()
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = self._write_sonameless_hook()
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        # Upstream ships no tests/ or autotests/ directory for this release,
        # so there is no ctest suite to run (R51 declaration in notes.md).
        self._bake_needed_path_stubs()

    def _bake_needed_path_stubs(self):
        """Fix CI-fatal DT_NEEDED absolute paths baked into published
        binary packages (kio/kxmlgui 6.26.0 line).

        The published KF6 libraries record absolute DT_NEEDED entries
        pointing at the *build-time* conan cache package dirs. On any other
        machine those paths do not exist and the loader aborts before
        LD_LIBRARY_PATH is even consulted. Fix: scan every dependency .so
        for absolute DT_NEEDED entries; for each one whose file does not
        exist, create the exact parent directory and symlink the
        actually-available same-named library from the real dependency
        package into it. Paths outside the user-writable home or /data are
        skipped (kcmutils 6.26.0 precedent).
        """
        import struct

        def _needed_entries(so_path):
            """Parse DT_NEEDED from the .dynamic section (readelf-free)."""
            try:
                with open(so_path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF":
                return []
            is64 = data[4] == 2
            if not is64:
                return []
            e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
            dyn_off = dyn_sz = 0
            dynstr_off = 0
            for i in range(e_shnum):
                sh = e_shoff + i * e_shentsize
                sh_type = struct.unpack_from("<I", data, sh + 4)[0]
                if sh_type == 6:  # SHT_DYNAMIC
                    dyn_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
                    dyn_sz = struct.unpack_from("<Q", data, sh + 0x20)[0]
                elif sh_type == 3:  # SHT_STRTAB (first one is .dynstr in practice)
                    if dynstr_off == 0:
                        dynstr_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
            if not dyn_off or not dynstr_off:
                return []
            needed = []
            count = dyn_sz // 16
            for i in range(count):
                d_tag = struct.unpack_from("<Q", data, dyn_off + i * 16)[0]
                d_val = struct.unpack_from("<Q", data, dyn_off + i * 16 + 8)[0]
                if d_tag == 1:  # DT_NEEDED
                    end = data.index(b"\x00", dynstr_off + d_val)
                    name = data[dynstr_off + d_val : end].decode("utf-8", "replace")
                    needed.append(name)
            return needed

        so_files = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                so_files.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        so_files.extend(glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*")))

        available = {}
        for path in so_files:
            available[os.path.basename(path)] = path

        stubs = 0
        for so in so_files:
            for needed in _needed_entries(so):
                if not needed.startswith("/"):
                    continue  # relative NEEDED goes through the search path
                if os.path.exists(needed):
                    continue  # already resolvable
                base = os.path.basename(needed)
                target = available.get(base)
                if not target:
                    continue
                parent = os.path.dirname(needed)
                home = os.path.expanduser("~")
                if not (parent.startswith(home) or parent.startswith("/data")):
                    continue  # outside writable roots; skip
                try:
                    os.makedirs(parent, exist_ok=True)
                    if not os.path.lexists(needed):
                        os.symlink(target, needed)
                        stubs += 1
                except OSError:
                    continue
        if stubs:
            self.output.info("baked DT_NEEDED path stubs created: %d" % stubs)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()

    # HarmonyOS PC's musl loader refuses to dlopen any ELF whose bytes differ
    # from what the linker produced (dlopen fails with EACCES even for a
    # 1-byte tail change or a no-op patchelf rewrite). Post-build ELF editing
    # (patchelf --replace-needed / in-place dynstr rewrites) therefore cannot
    # strip the absolute cache-path DT_NEEDED entries that CMake emits when
    # linking against SONAME-less dependency libs (kcoreaddons/ki18n 6.26.0).
    # Instead, inject a CMAKE_PROJECT_INCLUDE hook that rewrites those
    # imported targets to bare "-l<name>" link items plus INTERFACE -L dirs at
    # generation time, so lld records bare basenames in DT_NEEDED from the
    # start and nothing ever needs patching afterwards.
    _SONAMELESS_HOOK = """
macro(_ohpcd_sonameless_to_bare)
  set(_dirs "")
  set(_tgts KF6::CoreAddons KF6::I18n KF6::I18nLocaleData KF6::Codecs
      KF6::ConfigCore KF6::ConfigGui KF6::ItemViews KF6::IconThemes
      KF6::IconThemesEngine KF6::XmlGui KF6::KCMUtils KF6::QuickAddons
      KF6::Archive KF6::GuiAddons KF6::WidgetsAddons KF6::ColorScheme
      KF6::WindowSystem KF6::Service KF6::JobWidgets KF6::Completion
      KF6::GlobalAccel KF6::Notifications KF6::Actions KF6::Crash
      KF6::DBusAddons KF6::Sonnet KF6::TextWidgets KF6::NewStuffCore
      KF6::NewStuff KF6::Purpose KF6::PurposeWidgets)
  foreach(tgt ${_tgts})
    if(TARGET ${tgt})
      get_property(son TARGET ${tgt} PROPERTY IMPORTED_SONAME_RELEASE)
      get_property(loc TARGET ${tgt} PROPERTY IMPORTED_LOCATION_RELEASE)
      if(NOT son AND loc)
        get_filename_component(nm "${loc}" NAME)
        get_filename_component(dir "${loc}" DIRECTORY)
        string(LENGTH "${nm}" _nm_len)
        math(EXPR _ln_len "${_nm_len} - 6")
        string(SUBSTRING "${nm}" 3 ${_ln_len} _ln)
        set_property(TARGET ${tgt} PROPERTY IMPORTED_LOCATION_RELEASE "-l${_ln}")
        set_property(TARGET ${tgt} PROPERTY IMPORTED_LOCATION "-l${_ln}")
        get_property(iface TARGET ${tgt} PROPERTY INTERFACE_LINK_LIBRARIES)
        if(NOT iface)
          set(iface "")
        endif()
        set_property(TARGET ${tgt} PROPERTY INTERFACE_LINK_LIBRARIES "-L${dir};-l${_ln};${iface}")
        list(APPEND _dirs "${dir}")
      endif()
    endif()
  endforeach()
  if(_dirs)
    list(REMOVE_DUPLICATES _dirs)
    set(_lf "")
    foreach(d ${_dirs})
      string(APPEND _lf " -L${d}")
    endforeach()
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS}${_lf}")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS}${_lf}")
    set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS}${_lf}")
  endif()
endmacro()
cmake_language(DEFER DIRECTORY ${CMAKE_SOURCE_DIR} CALL _ohpcd_sonameless_to_bare)
"""

    def _write_sonameless_hook(self):
        gen_dir = self.folders.generators_folder or self.folders.build_folder
        hook = os.path.join(gen_dir, "ohpcd_sonameless_hook.cmake")
        with open(hook, "w") as f:
            f.write(self._SONAMELESS_HOOK)
        return hook

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["kaccounts6"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
