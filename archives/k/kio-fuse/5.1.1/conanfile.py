#!/usr/bin/env python3
"""Conan recipe for kio-fuse 5.1.1 on HarmonyOS PC.

kio-fuse exposes KIO URLs (remote/archive/...) as a real userspace FUSE
filesystem: the libexec kio-fuse daemon mounts a kernel FUSE filesystem and
serves the file I/O through KF6::KIOCore (KIO::FileJob or the FIO worker).
The package ships the daemon, the org.kde.KIOFuse D-Bus activation service
file and the kio-fuse systemd user unit.

OHOS-specific adaptations (recipe layer + two minimal source patches):
  - patches 0001+0002 wire up Qt6::DBus: KIOFuseService uses
    QDBusConnection/QDBusMessage, and the OHOS kio/6.26.0 is built with
    USE_DBUS=OFF, so it does not export the transitive Qt6DBus link that a
    DBus-enabled kio provides. 0002 adds the DBus component to the
    top-level find_package(Qt6) — the versionless Qt::DBus alias is only
    visible in the directory scope that created it, and the one created by
    tests/ is out of reach for src/ — 0001 then links Qt::DBus into the
    daemon. Qt6::DBus is only available from qtbase-sql-dbus/6.11.1
    (qtbase/6.11.1 ships FEATURE_dbus=OFF and no Qt6DBus cmake module).
  - DT_NEEDED hygiene: after linking, every absolute DT_NEEDED entry of
    the daemon is rewritten to the plain library name with patchelf
    (/data/service/hnp/bin/patchelf on the OHOS images). The platform
    kcoreaddons package (6.26.0) ships its library without a DT_SONAME,
    so linking its imported target bakes the build machine's cache path
    into DT_NEEDED as an absolute path (L5b violation, not portable);
    the rewritten bare name resolves through LD_LIBRARY_PATH like the
    rest of the dependency set.
  - The installed ELF tree is re-signed in package(): cmake.install
    rewrites the RUNPATH of the daemon, which invalidates the
    toolchain-stamped .codesign section and the OHOS kernel refuses to
    exec() the file (EPERM, device-probed in create #9). package()
    strips .codesign with llvm-objcopy and re-signs with
    binary-sign-tool (kscreenlocker/kscreen 6.7.2 precedent).
  - BUILD_WITH_QT6=ON: ECM's QtVersionOption defaults the Qt version option
    to Qt5 while the requested ECM version is below 5.240 (kio-fuse calls
    find_package(ECM 5.96)); the KF6 6.26 baseline is Qt6-only.
  - CMAKE_INSTALL_LIBDIR=lib and KDE_INSTALL_LIBEXECDIR=libexec are pinned:
    ECM defaults the libexec dir to "libexec" on UNIX and "bin" on other
    systems, and with the device's CMAKE_SYSTEM_NAME the UNIX check fails
    (the daemon would land in bin/). Pinning keeps the upstream/KDE layout
    that the D-Bus service file and the systemd unit embed.
  - libfuse/3.18.2 links statically (ohpcd binary: shared=False, fPIC=True,
    utils=False, so no fusermount3): a shared libfuse3 would need the
    meson symlink chain (libfuse3.so -> libfuse3.so.3.x), which the OHOS
    HMDFS sandbox rejects (symlink() EPERM); the static archive keeps the
    daemon self-contained (no libfuse3 DT_NEEDED). libfuse/3.18.2 also
    carries the HarmonyOS portability patches (pthread_cancel guards,
    HarmonyOS mount path selection).
  - A hand-written fuse3.pc is placed in the generators folder (and
    PKG_CONFIG_PATH points there during configure): the canonical
    libfuse3.pc exposes the header subdirectory
    (Cflags: -I${includedir}/fuse3) because the sources use plain
    #include <fuse_lowlevel.h>; a dependency-generated .pc with a bare
    -I${includedir} cannot resolve those includes (libappimage 1.0.4
    hand-written .pc precedent).
  - Shared libdbus-1.so.3 is vendored (built from the official dbus 1.14.10
    sources inside this recipe, kglobalacceld 6.7.2 mechanism): the OHOS
    qtbase builds Qt6DBus with dbus-linked=OFF, so libQt6DBus dlopen()s
    "libdbus-1.so.3" at runtime while the ohpcd registry only publishes a
    static libdbus-1.a. The sub-build forces CMAKE_SYSTEM_NAME=OHOS so the
    library keeps its DT_SONAME (L5a gate); the version chain CMake then
    wants to materialize by symlink is completed with copies instead,
    because the sandbox denies symlink() (EPERM, see libfuse3 bullet).
    Can be dropped once a shared dbus package exists on the registry.
  - Upstream tests: BUILD_TESTING=ON really compiles both fileopstests
    (Qt6Test/Qt6DBus link + qt_add_dbus_interface code generation are
    exercised at configure/build level), but neither can run inside the
    OHOS app sandbox: mounting a kernel FUSE filesystem is denied by
    policy — open("/dev/fuse") fails with EACCES and mount(2) is killed
    with SIGSYS by seccomp (device-probed 2026-10-16, see notes.md) — and
    the ctest commands are additionally wrapped in dbus-run-session, which
    the sandbox does not have. The two tests are excluded from the ctest
    invocation with the reasons shown in the build log; the packaged
    daemon's real runtime behavior is covered by test_package on device.
  - ECM_MODULE_PATH set explicitly (the CMakeDeps-generated ECMConfig does
    not propagate it) and a hand-written conan_cmakedeps_paths.cmake
    (qtbase/qtbase-sql-dbus use cmake_find_mode=none).
  - Ninja generator: the OHOS port of GNU make 4.4.1 uses an mkfifo-based
    jobserver which the sandbox denies (kglobalacceld/kcrash precedent).
"""
import glob
import io
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class KioFuseConan(ConanFile):
    name = "kio-fuse"
    version = "5.1.1"
    description = "KIO FUSE: access KIO URLs as a userspace FUSE filesystem"
    license = "GPL-3.0-or-later"
    homepage = "https://invent.kde.org/system/kio-fuse"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core/DBus/Test come from qtbase-sql-dbus (superset qtbase
        # build with FEATURE_dbus=ON; qtbase/6.11.1 ships dbus=OFF).
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6::KIOCore + KF6::CoreAddons; KF6KIOConfig.cmake
        # find_dependency()s kconfig/ki18n/kservice/kcrash, which the graph
        # pulls transitively through kio.
        self.requires("kio/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        # The OHOS SDK lld links against libxml2.so.16 (SONAME of
        # libxml2/2.15.3); declared so its lib dir can be injected into
        # LD_LIBRARY_PATH (kio 6.26.0 precedent).
        self.requires("libxml2/2.15.3")
        # FUSE 3 headers/libs, static build (see docstring).
        self.requires("libfuse/3.18.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored shared libdbus-1.so.3 runtime for Qt6DBus (dlopen-based
        # loading on OHOS, see docstring). Fixed URL + SHA256.
        get(self,
            url="https://dbus.freedesktop.org/releases/dbus/dbus-1.14.10.tar.xz",
            sha256="ba1f21d2bd9d339da2d4aa8780c09df32fea87998b73da24f49ab9df1e36a50f",
            strip_root=True, destination="dbus-src")

    def _build_vendored_libdbus(self):
        """Build the shared dbus-1 client library (no expat needed)."""
        src = os.path.join(self.source_folder, "dbus-src")
        bld = os.path.join(self.build_folder, "dbus-build")
        gen = self.generators_folder
        # The bundled CMake helper of this conan version cannot configure a
        # custom source/build folder pair, so drive cmake directly, pointing
        # at the same conan_toolchain (Ninja generator, OHOS clang).
        variables = {
            "BUILD_SHARED_LIBS": "ON",
            "DBUS_BUILD_TESTS": "OFF",
            "DBUS_BUILD_TOOLS": "OFF",
            "DBUS_ENABLE_DOXYGEN_DOCS": "OFF",
            "DBUS_ENABLE_XML_DOCS": "OFF",
            "DBUS_ENABLE_X11": "OFF",
            "DBUS_ENABLE_SYSTEMD": "OFF",
            "DBUS_ENABLE_SELINUX": "OFF",
            "DBUS_ENABLE_APPARMOR": "OFF",
            "DBUS_ENABLE_EMBEDDED_TESTS": "OFF",
            "DBUS_ENABLE_MODULAR_TESTS": "OFF",
            "DBUS_ENABLE_INSTALLED_TESTS": "OFF",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            # Force the OHOS platform module: dbus must not pick its
            # Windows transport, and the module provides the SONAME rule
            # that keeps DT_SONAME on the library (L5a gate) — without a
            # platform module CMake is "unknown system" here and drops
            # VERSION/SOVERSION entirely. The resulting symlink chain is
            # completed with copies below (symlink() EPERM on OHOS).
            "CMAKE_SYSTEM_NAME": "OHOS",
            "DBUS_SESSION_SOCKET_DIR": "/tmp",
        }
        args = [
            "cmake", "-G", "Ninja",
            "-S", src, "-B", bld,
            f"-DCMAKE_TOOLCHAIN_FILE={os.path.join(gen, 'conan_toolchain.cmake')}",
        ]
        args += [f"-D{k}={v}" for k, v in variables.items()]
        with self._cmake_build_env().vars(self).apply():
            self.run(" ".join(args))
            try:
                self.run(f'cmake --build "{bld}" --target dbus-1')
            except ConanException:
                # symlink() is denied on OHOS (EPERM), so the version
                # chain (...so -> .so.3 -> .so.3.32.4) cannot be created
                # and the build fails after the real library was linked.
                # Complete the chain with copies (same ELF, DT_SONAME
                # intact); re-raise only if the library was never produced.
                import shutil
                lib_dir = os.path.join(bld, "lib")
                candidates = [
                    p for p in glob.glob(os.path.join(lib_dir, "libdbus-1.so*"))
                    if os.path.isfile(p) and not os.path.islink(p)
                ]
                real = max(candidates, key=lambda p: len(os.path.basename(p)),
                           default=None)
                if not real or not os.path.getsize(real):
                    raise
                for name in ("libdbus-1.so.3", "libdbus-1.so"):
                    dst = os.path.join(lib_dir, name)
                    if not os.path.lexists(dst):
                        shutil.copy2(real, dst)
                        self.output.info(
                            f"symlink() EPERM on OHOS: created {name} as a copy")

    def _vendored_libdbus_dir(self):
        return os.path.join(self.build_folder, "dbus-build", "lib")

    def _write_fuse3_pc(self):
        """Hand-written fuse3.pc for the static libfuse (see docstring)."""
        fuse = self.dependencies.get("libfuse")
        if not fuse or not fuse.package_folder:
            return
        prefix = fuse.package_folder.replace("\\", "/")
        pc = (
            f"prefix={prefix}\n"
            f"includedir={prefix}/include\n"
            f"libdir={prefix}/lib\n"
            "\n"
            "Name: fuse3\n"
            "Description: Filesystem in Userspace (libfuse 3)\n"
            "Version: 3.18.2\n"
            f"Libs: -L{prefix}/lib -lfuse3\n"
            f"Cflags: -I{prefix}/include/fuse3 -I{prefix}/include\n"
        )
        save(self, os.path.join(self.generators_folder, "fuse3.pc"), pc)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_TESTING"] = "ON"
        # ECM QtVersionOption defaults to Qt5 for ECM requests below 5.240
        # (kio-fuse asks for 5.96); KF6 6.26 is Qt6-only.
        tc.variables["BUILD_WITH_QT6"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Deterministic install layout for the libexec daemon, the D-Bus
        # service file and the systemd unit.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # ECM defaults the libexec dir to "libexec" on UNIX and "bin"
        # otherwise; with the device's CMAKE_SYSTEM_NAME the UNIX check
        # fails, so pin the upstream/KDE layout explicitly (the D-Bus
        # service file and the systemd unit embed this path).
        tc.variables["KDE_INSTALL_LIBEXECDIR"] = "libexec"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt_pkgs = [d for d in self.dependencies.values()
                   if d.package_folder and os.path.isdir(os.path.join(d.package_folder, "lib", "cmake"))]
        if qt_pkgs:
            lines = []
            # qtbase/qtbase-sql-dbus use cmake_find_mode=none, so CMakeDeps
            # does not emit conan_cmakedeps_paths.cmake; create it manually.
            for dep in qt_pkgs:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
            # qtbase-sql-dbus must win the find_package(Qt6) lookup: it is
            # the only provider of Qt6::DBus (qtbase ships FEATURE_dbus=OFF),
            # and it also ships the full Core/Test set.
            sqldbus = self.dependencies.get("qtbase-sql-dbus")
            if sqldbus:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{sqldbus.package_folder}/lib/cmake")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()
        if self.settings.os == "OHOS":
            self._write_fuse3_pc()

    def _library_runtime_env(self):
        runtime_env = Environment()
        if self.settings.os == "OHOS":
            # Vendored shared libdbus-1.so.3 must be resolvable when Qt6DBus
            # dlopen()s it (see docstring).
            vendored = self._vendored_libdbus_dir()
            if os.path.isdir(vendored):
                runtime_env.prepend_path("LD_LIBRARY_PATH", vendored)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        for rel in ("bin", "lib", "src", "tests"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH may contain an
            # incompatible libc++_shared.so which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the
            # compatible libc++ first (kconfig/kcrash/kglobalacceld
            # precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            # pkg_check_modules(FUSE3 REQUIRED fuse3) must find the
            # hand-written fuse3.pc from the generators folder.
            build_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        return build_env

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so other
        # platforms are unaffected (kcrash/kglobalacceld precedent).
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            self._build_vendored_libdbus()
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._fix_absolute_needed()
            self._run_upstream_tests()

    def _fix_absolute_needed(self):
        """Rewrite absolute DT_NEEDED entries of the daemon to plain names.

        The platform kcoreaddons/6.26.0 library ships without a DT_SONAME,
        so linking its imported target records the build machine's cache
        path as an absolute DT_NEEDED entry: not portable, and an L5b
        gate violation. Each such entry is rewritten with patchelf to the
        bare library name, which the runtime linker resolves through
        LD_LIBRARY_PATH like the other dependencies. Runs before
        cmake.install() so the packaged daemon carries the fix.
        """
        matches = glob.glob(
            os.path.join(self.build_folder, "**", "bin", "kio-fuse"),
            recursive=True,
        )
        assert matches, "kio-fuse binary not found under " + self.build_folder
        binary = sorted(matches)[0]
        patchelf = "/data/service/hnp/bin/patchelf"
        buf = io.StringIO()
        self.run(
            '"{}" --print-needed "{}"'.format(patchelf, binary),
            stdout=buf,
            stderr=buf,
        )
        fixed = []
        for entry in buf.getvalue().splitlines():
            entry = entry.strip()
            if entry.startswith("/"):
                self.run(
                    '"{}" --replace-needed "{}" "{}" "{}"'.format(
                        patchelf, entry, os.path.basename(entry), binary
                    )
                )
                fixed.append("{} -> {}".format(entry, os.path.basename(entry)))
        self.output.info(
            "DT_NEEDED check on {}: {} absolute entr{} rewritten{}".format(
                binary,
                len(fixed),
                "y" if len(fixed) == 1 else "ies",
                (": " + "; ".join(fixed)) if fixed else "",
            )
        )

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # Both upstream fileopstests need a working kernel FUSE mount: the
        # OHOS app sandbox denies it at the syscall policy level
        # (open("/dev/fuse") -> EACCES; mount(2) -> SIGSYS/seccomp) and the
        # ctest commands are additionally wrapped in dbus-run-session, which
        # the sandbox does not provide. The tests still compile with
        # BUILD_TESTING=ON (Qt6Test/Qt6DBus/qt_add_dbus_interface exercised);
        # they are excluded from the run and the reasons are recorded in
        # notes.md (kio/kdbusaddons environment-limitation precedent).
        excluded_tests = ("fileopstest-cache", "fileopstest-filejob")
        exclude_re = "^({})$".format("|".join(excluded_tests))
        self.output.info(
            "Excluding OHOS-sandbox-incompatible upstream tests: {} "
            "(kernel FUSE mount denied by the app sandbox; dbus-run-session "
            "unavailable)".format(", ".join(excluded_tests))
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=ignore '
                '-E "{}"'.format(self.build_folder, exclude_re),
                ignore_errors=True,
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()
        if self.settings.os == "OHOS":
            # Ship the vendored shared libdbus-1.so.3 (Qt6DBus dlopens it at
            # runtime; the registry only has a static libdbus-1.a).
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            for path in sorted(glob.glob(os.path.join(self._vendored_libdbus_dir(), "libdbus-1.so*"))):
                target = os.path.join(lib_dir, os.path.basename(path))
                if os.path.islink(path):
                    if not os.path.lexists(target):
                        os.symlink(os.readlink(path), target)
                elif not os.path.exists(target):
                    shutil.copy2(path, target)
            # cmake.install rewrote the RUNPATH of the shipped daemon, which
            # invalidates the toolchain-stamped .codesign section; the OHOS
            # kernel then refuses to exec() it (EPERM). Re-sign the tree
            # (kscreenlocker/kscreen 6.7.2 precedent).
            self._sign_ohos_elf_tree(self.package_folder)

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
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package_info(self):
        # kio-fuse installs a libexec daemon plus D-Bus/systemd service
        # files; there is no consumable library or header to export.
        self.cpp_info.set_property("cmake_find_mode", "none")
