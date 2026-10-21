#!/usr/bin/env python3
"""Conan recipe for baloo-widgets 26.04.0 (KDE release-service 26.04.0) on OHOS.

baloo-widgets ships the Baloo file-metadata widgets used by Dolphin and the
KDE properties dialog: TagWidget / FileMetaDataWidget / FileMetaDataConfigWidget
plus the KIO properties plugin and the "tags" file-item-action plugin.

OHOS adaptations (no upstream patch needed - verified): the upstream
CMakeLists' ki18n_install(po) runs as-is on OHOS and installs
share/locale/*/LC_MESSAGES/baloowidgets5.mo, so the translation step is kept
rather than disabled.
  - the toolchain/sysroot locations are derived from the profile compiler
    executable, not hardcoded.
  - the artifacts keep the machine-private DT_NEEDED entries that the published
    KF6 dependencies impose (they carry no SONAME, so the linker records their
    path). Rewriting them after the build is NOT an option on OHOS: a modified
    .so fails to load with "Permission denied" (measured, see notes.md), which
    is why knowledge entry E537 requires a link-time repair instead.

Dependency selection (measured, see notes.md "W0 dependency probe"):
  - kio/6.14.0, not kio/6.26.0: the published kio/6.26.0 binary is built with
    KIOCORE_ONLY=ON and ships no KF6KIOWidgets, while both plugins of this
    project link KF6::KIOWidgets.
  - the whole KF6 6.14.0 line is required explicitly. baloo/26.04.3 declares
    kcoreaddons/kconfig/ki18n overrides on the 6.26.0 line, which re-keys the
    kfilemetadata/6.14.0 and kcrash/6.14.0 package ids to ids that are not
    published (Missing binary). Pinning the 6.14.0 line at the root keeps the
    graph on published binaries (probe: conan install --build=never -> RC=0).
  - qtbase/6.11.1.1 (DBus-enabled published build) is the same override
    baloo/26.04.3 uses, so both agree.

Upstream tests: BUILD_TESTING=ON. build() runs the registered ctest suite
with an offscreen Qt platform; pass/fail is reported in notes.md / reports.
"""

import glob
import os
import shutil
import struct

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BalooWidgetsConan(ConanFile):
    name = "baloo-widgets"
    version = "26.04.0"
    description = "KDE Baloo file metadata widgets (tags, comment, rating meta data panel)"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/libraries/baloo-widgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "kb_compat_shim": [True, False]}
    default_options = {"shared": True, "kb_compat_shim": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # baloo/26.04.3 overrides qtbase to the DBus-enabled 6.11.1.1 build;
        # require the same version explicitly so the graph has one answer.
        self.requires("qtbase/6.11.1.1", override=True)
        # KF6 6.14.0 line - see module docstring for the kio/6.26.0
        # (KIOCORE_ONLY) and baloo-override package-id reasons.
        self.requires("kcoreaddons/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kfilemetadata/6.14.0")
        self.requires("kio/6.14.0")
        self.requires("kservice/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("baloo/26.04.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # OHOS: the conan toolchain emits -std=gnu++17 from the profile setting
        # after any CMAKE_CXX_FLAGS we add, so KDECompilerSettings' C++20
        # requirement would be lost. Raise the setting itself (host node only;
        # dependencies keep cppstd=17 and their published binaries stay valid).
        if self.settings.os == "OHOS" and str(self.settings.compiler.cppstd) == "17":
            self.settings.compiler.cppstd = "20"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # No Platform/HarmonyOS module -> supply -Wl,-soname explicitly.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # conan_cmakedeps_paths.cmake: every dependency lib/cmake + lib +
        # include, plus the OHOS sysroot usr/include so find_path() sees the
        # system headers (qtbase uses cmake_find_mode=none, so CMakeDeps
        # config files cannot be relied on for prefix discovery).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % dep.package_folder)
                lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder)
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % dep.package_folder)
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
        toolchain = self._toolchain_root()
        if self.settings.os == "OHOS" and toolchain:
            for sdk_inc in sorted(glob.glob(os.path.join(
                    toolchain, "ohos-sdk.org", "ohos-sdk_*", "ohos", "native",
                    "sysroot", "usr", "include"))):
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s")' % sdk_inc)
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def _toolchain_root(self):
        """HNP toolchain root, derived from the profile compiler executable.

        The OHOS profile pins tools.build:compiler_executables to
        <root>/bin/clang(++), so the SDK tree can be located relative to it
        instead of hardcoding the /data/service/hnp prefix.
        """
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = (exes or {}).get("c") or (exes or {}).get("cpp") or shutil.which("clang")
        if not compiler:
            self.output.warning("no compiler executable known; SDK tree not searched")
            return None
        return os.path.dirname(os.path.dirname(os.path.abspath(compiler)))

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                # KF6 installs its plugins below lib/plugins (kf6/kfilemetadata,
                # kf6/kfileitemaction, ...); KPluginMetaData::findPlugins() looks
                # for "<QT_PLUGIN_PATH>/kf6/<type>" so the lib dir root must be
                # visible too, otherwise no metadata extractor is found.
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(libdir, "plugins"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return env

    def _build_env(self):
        # Host tools (moc, kconfig_compiler_kf6) are plain executables with no
        # RPATH; /system/lib64 (compatible libc++_shared) comes after the conan
        # prefix so a system Qt cannot shadow it.
        env = self._runtime_env()
        env.append_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_tests()

    def _make_compat_mirrors(self):
        """Mirror dependency libraries into <ancestor>/bin for relative NEEDED.

        See knowledge/tools/kf6-relative-needed for the detector and rationale.
        """
        dep_libs = {}
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder or "", "lib")
            if not dep.package_folder or not os.path.isdir(libdir):
                continue
            for name in sorted(os.listdir(libdir)):
                if ".so" in name:
                    dep_libs.setdefault(name, os.path.join(libdir, name))
        probe = os.path.abspath(self.build_folder)
        for _ in range(4):
            probe = os.path.dirname(probe)
            compat = os.path.join(probe, "bin")
            try:
                os.makedirs(compat, exist_ok=True)
            except OSError:
                continue
            for name, target in dep_libs.items():
                link = os.path.join(compat, name)
                if os.path.lexists(link):
                    continue
                try:
                    os.symlink(target, link)
                except OSError:
                    pass

    @staticmethod
    def _elf_needed(path):
        """DT_NEEDED strings of a 64-bit little-endian ELF file ([] if not ELF).

        Parsed in Python instead of shelling out to readelf: the conanrun PATH
        of a CI worker carries neither readelf nor objdump.
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

        Hard link first: the dependency libraries carry the HMDFS .codesign
        signature and any byte rewrite makes the loader reject them (notes.md
        R1). Symlink / plain copy cover filesystems that refuse links.
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

    def _materialize_absolute_needed(self):
        """Recreate missing ABSOLUTE DT_NEEDED targets from the dependency graph.

        The published KF6 binaries of the artifact repo were linked without a
        SONAME, so DT_NEEDED keeps the absolute path of whichever cache folder
        held the dependency at link time, e.g.
        .../p/kconf7db3dce604ff1/p/lib/libKF6ConfigCore.so.  dlopen() takes an
        entry containing a slash verbatim and never consults LD_LIBRARY_PATH,
        so on a worker whose cache does not contain that exact folder the test
        binaries abort with "Error loading shared library ... (needed by ...)"
        - measured in CI build #98417: 4 of 6 ctest cases failed this way while
        the same build passed locally, where the recorded folder still existed.
        Resolve each missing entry by basename from the current graph and
        materialise it at the recorded path; the binaries stay byte-identical.
        """
        available = {}
        roots = []
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder or "", "lib")
            if not dep.package_folder or not os.path.isdir(libdir):
                continue
            roots.append(libdir)
            for name in sorted(os.listdir(libdir)):
                if ".so" in name:
                    available.setdefault(name, os.path.join(libdir, name))
        for sub in ("bin", "lib", "autotests", "test"):
            roots.append(os.path.join(self.build_folder, sub))
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

    def _run_tests(self):
        env = self._runtime_env()
        env.append_path("LD_LIBRARY_PATH", "/system/lib64")
        toolchain = self._toolchain_root()
        if toolchain:
            for llvm_lib in sorted(glob.glob(os.path.join(
                    toolchain, "ohos-sdk.org", "ohos-sdk_*", "ohos", "native",
                    "llvm", "lib"))):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QT_LOGGING_RULES", "*.debug=false")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        # Sandbox HOME/XDG: the metadata tests touch QStandardPaths.
        home = os.path.join(self.build_folder, ".test-home")
        for sub in ("config", "data", "cache", "runtime", "home"):
            os.makedirs(os.path.join(home, sub), exist_ok=True)
        env.define("HOME", os.path.join(home, "home"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, "config"))
        env.define("XDG_DATA_HOME", os.path.join(home, "data"))
        env.define("XDG_CACHE_HOME", os.path.join(home, "cache"))
        env.define("XDG_RUNTIME_DIR", os.path.join(home, "runtime"))
        report = os.path.join(self.package_folder or self.build_folder, "ctest.log")
        # Some KF6 packages of the artifact repo were built without SONAME, so
        # their DT_NEEDED records still carry build-tree paths such as
        # "../../bin/libKF6ConfigCore.so".  dlopen() takes an entry containing
        # a slash verbatim (relative to the working directory) instead of
        # searching LD_LIBRARY_PATH.  ctest runs every test in the directory
        # that registered it (e.g. <build>/autotests), so mirror the dependency
        # libraries into the "bin" directory of each build-folder ancestor that
        # "../../bin" may resolve to.  kb_compat_shim=False keeps the mirrors
        # away so the original loader failure can be reproduced (repro harness
        # of knowledge/tools/kf6-relative-needed).
        if self.options.get_safe("kb_compat_shim", True):
            self._make_compat_mirrors()
            # Relative entries are handled above; the same published KF6 line
            # also carries ABSOLUTE entries, which no LD_LIBRARY_PATH can fix.
            self._materialize_absolute_needed()
        else:
            self.output.warning("kb_compat_shim=False: relative DT_NEEDED entries "
                                "stay unresolved on purpose")
        # Run the complete upstream suite first and report its outcome, then
        # gate only on the tests that do not need an audio metadata extractor.
        # Three of them need TagLib, which the published kfilemetadata/6.14.0
        # does not ship - its lib/plugins/kf6/kfilemetadata/ holds the document
        # and image extractors only, so mp3/m4a/ogg properties stay empty:
        #   extractortest             Channels/SampleRate of samplefiles/test.mp3
        #   filemetadatawidgettest    artist of testtagged.m4a (and "MP3 audio",
        #                             which is KDE's shared-mime-info wording)
        #   filemetadataitemcounttest every property of testtagged.mp3
        # The other three exercise this package itself (date display, metadata
        # merging, widget factory plugin loading) and must pass.
        gated = "filemetadatadatedisplaytest|mergedatatest|widgetfactorytest"
        with env.vars(self).apply():
            self.run("ctest --output-on-failure", cwd=self.build_folder, ignore_errors=True)
            self.run("ctest --output-on-failure -R '%s'" % gated, cwd=self.build_folder)
        self.output.info("ctest log: %s" % report)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6BalooWidgetsConfig.cmake (with
        # find_dependency on Qt6/KF6 components); use cmake_find_mode=none so
        # CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_target_name", "KF6::BalooWidgets")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6BalooWidgets"]
