#!/usr/bin/env python3
"""Conan recipe for modemmanager-qt 6.28.0 on HarmonyOS PC.

modemmanager-qt is the KDE Frameworks 6 Qt binding of the ModemManager D-Bus
API: libKF6ModemManagerQt.so plus the camel-case ModemManagerQt headers
(Manager, Modem, Sim, Sms, Bearer, Modem3gpp, ...). It talks to the
org.freedesktop.ModemManager1 service over D-Bus; only the public
ModemManager enum/flag headers are consumed, so nothing links libmm-glib.

Upstream build (CMake):
  - find_package(ECM 6.28.0 NO_MODULE)      -> tool_requires extra-cmake-modules/6.29.0
  - find_package(ModemManager 1.0 REQUIRED) -> cmake/FindModemManager.cmake,
    which is a PKG_SEARCH_MODULE(ModemManager) wrapper
  - find_package(Qt6 6.9.0 REQUIRED Core DBus Xml)

OHOS-specific adaptation:
  - Qt6 Core/DBus/Xml come from qtbase/6.11.1.1, the published binary whose
    Qt6DBus consumption gate (libQt6DBus.so + Qt6DBusConfig.cmake + a real
    CMake consumer linking Qt6::DBus) was verified on device (kdbusaddons
    6.29.0 precedent). Plain qtbase/6.11.1 is built with FEATURE_dbus=OFF.
  - FindModemManager resolves a pkg-config module literally named
    `ModemManager`. modemmanager/1.24.2 ships a headers-only ModemManager.pc
    (upstream meson pkg.generate with subdirs), but it lives inside the
    dependency package, off the default pkg-config search path, and its
    Cflags only carries -I${includedir}/ModemManager. generate() writes a
    matching ModemManager.pc into the generators folder, puts that folder on
    PKG_CONFIG_PATH and additionally exports -I${includedir}: the upstream
    sources include <ModemManager/ModemManager.h>, which on Linux resolves
    through the compiler's default /usr/include and has no equivalent when
    the headers live in the Conan cache. The extra -I is propagated to
    consumers through the exported target (src/CMakeLists.txt does
    target_include_directories(KF6ModemManagerQt PUBLIC
    ${MODEMMANAGER_INCLUDE_DIRS})).
  - qtbase uses cmake_find_mode=none, so CMakeDeps cannot contribute its
    lib/cmake to CMAKE_PREFIX_PATH; generate() writes
    conan_cmakedeps_paths.cmake itself (kcoreaddons/kdbusaddons precedent).
  - KF_IGNORE_PLATFORM_CHECK=TRUE bypasses KDE's platform allowlist (OHOS is
    not in the upstream list).
  - BUILD_TESTING=ON: the 10 upstream autotest programs (11 QTest functions)
    drive a FakeModem registered on the *session* bus (the static library is
    compiled with -DMMQT_STATIC=1, which switches every QDBusConnection from
    the system bus to the session bus). build() starts a private dbus-daemon
    on a unix socket and runs ctest against it. AF_UNIX bind is denied on
    HMDFS, so the socket is placed on the app sandbox tmpfs
    (/data/storage/el2/base); the recipe probes the candidate directories and
    only uses one where bind(2) succeeds. EXTERNAL auth over the unix socket
    is the mechanism QtDBus implements. The private bus comes from the
    build-context dbus/1.14.10.3 tool_requires: the .0/.1/.2 revisions of
    that recipe force the client library STATIC, while .3 keeps it shared
    and packages libdbus-1.so.3 next to bin/dbus-daemon. The shared library
    is needed at runtime because Qt6DBus resolves libdbus-1.so.3 with
    dlopen() and the FEATURE_dbus=ON qtbase binary carries no NEEDED entry
    for it; without it QDBusConnection reports "Not connected to D-Bus
    server" and the daemon never sees a client. The test environment
    therefore also prepends the tool package's lib dir to LD_LIBRARY_PATH.
  - L5 SONAME gate: CMake ships no Platform/HarmonyOS.cmake, so the ELF
    soname linker-flag variables are undefined and ECM's VERSION/SOVERSION
    properties are silently dropped; the recipe supplies the same values the
    Linux platform module uses (networkmanager-qt 6.26.0 precedent).

package_info():
  - cmake_find_mode=none: upstream installs a complete, relocatable
    KF6ModemManagerQtConfig.cmake (find_dependency on Qt6Core/Qt6DBus), which
    must not be shadowed by an incomplete generated config.
"""
import os
import shlex
import shutil
import socket
import subprocess
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# LD_PRELOAD shim for the private dbus-daemon used by the upstream autotests.
#
# The OHOS app sandbox runs as UID/GID 20020084, which has no entry in
# /etc/passwd or /etc/group. dbus-daemon resolves every EXTERNAL client in
# bus_policy_allow_unix_user() -> _dbus_unix_groups_from_uid(), and with no
# account entry that lookup fails, so the daemon rejects the connection with
# "Did not get any groups for UID 20020084" before the client can Hello.
# Preloading a synthetic entry for the *current* UID gives the daemon the
# account view it expects without touching any system file. Other UIDs are
# reported as not found, which is the same result musl returns on this device
# (there is no NSS). Test-only: never shipped in the package.
_PASSWD_SHIM_C = r"""
#define _GNU_SOURCE
#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static char shim_name[] = "currentUser";
static char shim_passwd[] = "x";
static char shim_gecos[] = "";
static char shim_shell[] = "/bin/sh";
static char shim_root[] = "/";

static int shim_is_self(uid_t uid)
{
    return uid == getuid() || uid == geteuid();
}

static void shim_fill(struct passwd *pwd, uid_t uid)
{
    const char *home = getenv("HOME");
    pwd->pw_name = shim_name;
    pwd->pw_passwd = shim_passwd;
    pwd->pw_uid = uid;
    pwd->pw_gid = getgid();
    pwd->pw_gecos = shim_gecos;
    pwd->pw_dir = (char *)(home != NULL ? home : shim_root);
    pwd->pw_shell = shim_shell;
}

int getpwuid_r(uid_t uid, struct passwd *pwd, char *buf, size_t buflen,
               struct passwd **result)
{
    (void)buf;
    (void)buflen;
    if (pwd == NULL || result == NULL) {
        errno = EINVAL;
        return EINVAL;
    }
    if (shim_is_self(uid)) {
        shim_fill(pwd, uid);
        *result = pwd;
        return 0;
    }
    *result = NULL;
    errno = 0;
    return 0;
}

int getpwnam_r(const char *name, struct passwd *pwd, char *buf, size_t buflen,
               struct passwd **result)
{
    (void)buf;
    (void)buflen;
    if (pwd == NULL || result == NULL) {
        errno = EINVAL;
        return EINVAL;
    }
    if (name != NULL && strcmp(name, shim_name) == 0) {
        shim_fill(pwd, getuid());
        *result = pwd;
        return 0;
    }
    *result = NULL;
    errno = 0;
    return 0;
}

int getgrouplist(const char *user, gid_t group, gid_t *groups, int *ngroups)
{
    if (user != NULL && strcmp(user, shim_name) == 0) {
        if (ngroups == NULL) {
            errno = EINVAL;
            return -1;
        }
        if (groups == NULL) {
            errno = EINVAL;
            return -1;
        }
        if (*ngroups < 1) {
            *ngroups = 1;
            return -1;
        }
        groups[0] = group;
        *ngroups = 1;
        return 1;
    }
    if (ngroups != NULL) {
        *ngroups = 0;
    }
    return -1;
}
"""


class ModemmanagerQtConan(ConanFile):
    name = "modemmanager-qt"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Qt bindings for the ModemManager D-Bus API"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/frameworks/modemmanager-qt"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _pc_name = "KF6ModemManagerQt"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core / DBus / Xml (Qt6DBus is REQUIRED upstream).
        self.requires("qtbase/6.11.1.1")
        # Public ModemManager headers (ModemManager.h / -enums.h / -version.h)
        # and the ModemManager.pc module consumed by cmake/FindModemManager.cmake.
        self.requires("modemmanager/1.24.2")

    def build_requirements(self):
        # ECM >= 6.28.0 is REQUIRED upstream; extra-cmake-modules/6.29.0 is the
        # published base for the KF6 path.
        self.tool_requires("extra-cmake-modules/6.29.0")
        # build-context dbus for the upstream autotests' private session bus.
        # dbus/1.14.10.3 is the shared-client-library revision of the recipe:
        # it ships both dbus-daemon and libdbus-1.so.3, which Qt6DBus
        # dlopen()s at runtime (the FEATURE_dbus=ON qtbase binary has no
        # NEEDED entry for it), so the test environment also needs the tool
        # package's lib dir. Build requirements do not affect package_id.
        self.tool_requires("dbus/1.14.10.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # Upstream rewrites CMAKE_CXX_FLAGS (variable_watch), so re-assert the
        # standard there; keep any flags the profile passes via
        # tools.build:cxxflags (ABI flags and similar) instead of dropping them.
        cxxflags = list(self.conf.get("tools.build:cxxflags", default=[], check_type=list))
        if "-std=c++20" not in cxxflags:
            cxxflags.append("-std=c++20")
        tc.variables["CMAKE_CXX_FLAGS"] = " ".join(cxxflags)

        # ── L5 SONAME gate: complete CMake's missing HarmonyOS platform module ──
        # See the module docstring. Without these variables CMake drops the
        # upstream ECM VERSION/SOVERSION properties (no DT_SONAME, no versioned
        # symlink chain, IMPORTED_NO_SONAME in the exported targets).
        if str(self.settings.os) == "OHOS":
            self._configure_ohos_shared_library_rules(tc)

        # pkg_search_module() needs a working pkg-config; pin the executable so
        # configure does not depend on the ambient PATH (R33).
        pkg_config = shutil.which("pkg-config") or "/data/service/hnp/bin/pkg-config"
        if os.path.isfile(pkg_config):
            tc.variables["PKG_CONFIG_EXECUTABLE"] = pkg_config

        # ECM's installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not; set it manually so KDEInstallDirs,
        # KDECMakeSettings, ECMGenerateQDoc, ... are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_modemmanager_pc()
        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake ships no Platform/HarmonyOS module, so no DT_SONAME is
        emitted and consumers record absolute conan-cache paths in DT_NEEDED.
        Restore the soname linker flags via CMAKE_USER_MAKE_RULES_OVERRIDE and
        suppress the versioned symlink chain: because upstream sets
        VERSION/SOVERSION through ecm_setup_version, CMake would otherwise
        create libKF6ModemManagerQt.so.6.28.0 -> .so.6 -> .so, which the
        OHOS/HMDFS user volume rejects (cmake_symlink_library: System Error:
        Permission denied, E330). CMAKE_PLATFORM_NO_VERSIONED_SONAME emits a
        single unversioned .so with the relocatable bare SONAME (ki18n/6.28.0
        and kservice/6.28.0 pattern)."""
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        with open(rules, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                    )
                )
                + "\n"
            )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        # The install step rewrites the DT_RUNPATH CMake emitted for the build
        # tree (zeros the old string in place, drops the dynamic entry). The
        # rewritten library cannot be dlopen()ed on the OHOS user volume:
        # "Error loading shared library ...: Permission denied" (EACCES),
        # although readelf reports a valid ELF. The build-tree file with the
        # original bytes loads fine, as does a package whose install step had
        # nothing to rewrite (kservice/6.28.0 build and package libs are
        # byte-identical). Emit no RPATH at all -- the loader finds the
        # dependencies through LD_LIBRARY_PATH, and build/package stay
        # byte-identical.
        toolchain.variables["CMAKE_SKIP_RPATH"] = "TRUE"

    # ── pkg-config module for find_package(ModemManager) ─────────────────

    def _write_modemmanager_pc(self):
        """Write the ModemManager pkg-config module FindModemManager searches.

        The modemmanager package ships a headers-only ModemManager.pc built by
        upstream meson pkg.generate(subdirs: mm_name); its Cflags is
        -I${includedir}/ModemManager. Two adjustments are needed for a Conan
        package:

          * the module must be on PKG_CONFIG_PATH (the generators folder is);
          * -I${includedir} must be exported as well, because the public
            headers are included as <ModemManager/ModemManager.h> (upstream
            relies on the compiler's default /usr/include there).

        ${includedir} is expanded by pkg-config from the absolute prefix, so
        the module stays correct for the cache path used at build time.
        """
        modemmanager = self.dependencies.get("modemmanager")
        if not modemmanager or not modemmanager.package_folder:
            raise ConanException(
                "modemmanager package folder is not available; cannot write "
                "the ModemManager.pc module required by FindModemManager.cmake"
            )
        prefix = modemmanager.package_folder.replace("\\", "/")
        content = "\n".join(
            [
                "prefix=" + prefix,
                "exec_prefix=${prefix}",
                "libdir=${prefix}/lib",
                "includedir=${prefix}/include",
                "",
                "Name: ModemManager",
                "Description: Common headers provided by ModemManager",
                "Version: " + str(modemmanager.ref.version),
                "Cflags: -I${includedir} -I${includedir}/ModemManager",
                "",
            ]
        )
        pc_path = os.path.join(self.generators_folder, "ModemManager.pc")
        with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info(f"wrote {pc_path} (prefix={prefix})")

    def _write_cmake_paths(self):
        prefixes, libraries, includes, modules = [], [], [], []

        def add(collection, value):
            value = value.replace("\\", "/")
            if value not in collection:
                collection.append(value)

        def add_package_folder(folder):
            if not folder:
                return
            add(prefixes, os.path.join(folder, "lib", "cmake"))
            add(prefixes, folder)
            add(libraries, os.path.join(folder, "lib"))
            add(includes, os.path.join(folder, "include"))
            add(modules, os.path.join(folder, "lib", "cmake"))

        # qtbase first so Qt6Core/DBus/Xml come from the FEATURE_dbus=ON build.
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            add_package_folder(qtbase.package_folder)

        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            if dep.ref.name == "qtbase":
                continue
            add_package_folder(dep.package_folder)

        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    # ── build environment ────────────────────────────────────────────────

    def _library_runtime_env(self):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # ECM's KDEInstallDirs6 executes the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64, so
            # /system/lib64 (compatible copy) is prepended.
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return build_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        # OHOS has no account entry for the sandbox UID; dbus-daemon needs one
        # to accept EXTERNAL clients (see _PASSWD_SHIM_C).
        self._passwd_shim = None
        if self.settings.os == "OHOS":
            self._passwd_shim = self._build_passwd_shim()
        self._run_upstream_tests()

    # ── upstream autotests (session-bus fake modem) ──────────────────────

    def _c_compiler_candidates(self):
        """C compilers to try for the passwd shim, CMake's pick first."""
        candidates = []

        def add(value):
            if value and value not in candidates:
                candidates.append(value)

        cache_path = os.path.join(self.build_folder, "CMakeCache.txt")
        if os.path.isfile(cache_path):
            try:
                with open(cache_path, "r", errors="replace") as handle:
                    for line in handle:
                        if line.startswith("CMAKE_C_COMPILER:"):
                            add(line.split("=", 1)[1].strip())
                            break
            except OSError:
                pass
        for name in ("clang", "cc", "gcc"):
            add(shutil.which(name))
        add(os.environ.get("CC"))
        import glob as _glob

        for candidate in sorted(
            _glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang")
        ):
            add(candidate)
        return candidates

    @staticmethod
    def _is_aarch64_elf(path):
        """True when `path` is an AArch64 ELF (the OHOS target machine)."""
        try:
            with open(path, "rb") as handle:
                header = handle.read(20)
        except OSError:
            return False
        return (
            len(header) == 20
            and header[:4] == b"\x7fELF"
            and int.from_bytes(header[18:20], "little") == 0xB7
        )

    def _build_passwd_shim(self):
        """Compile the account-database shim used by the private daemon."""
        directory = os.path.join(self.build_folder, "passwd-shim")
        os.makedirs(directory, exist_ok=True)
        source_path = os.path.join(directory, "passwd_shim.c")
        with open(source_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_PASSWD_SHIM_C)
        library_path = os.path.join(directory, "passwd_shim.so")

        errors = []
        for compiler in self._c_compiler_candidates():
            try:
                completed = subprocess.run(
                    [compiler, "-shared", "-fPIC", "-O2", "-o", library_path, source_path],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"{compiler}: {exc}")
                continue
            if completed.returncode == 0 and os.path.isfile(library_path):
                if self._is_aarch64_elf(library_path):
                    self.output.info(f"passwd shim built with {compiler}: {library_path}")
                    return library_path
                errors.append(f"{compiler}: produced a non-AArch64 ELF")
                continue
            detail = (completed.stderr or completed.stdout or "").strip()
            errors.append(f"{compiler}: rc={completed.returncode} {detail[:400]}")
        raise ConanException(
            "could not build the passwd shim required by dbus-daemon:\n" + "\n".join(errors)
        )

    def _dep_tool(self, name):
        """Absolute path of `name` from a dependency bin/ (host then build), else PATH."""
        for scope in (self.dependencies.values(), self.dependencies.build.values()):
            for dep in scope:
                if not dep or not dep.package_folder:
                    continue
                candidate = os.path.join(dep.package_folder, "bin", name)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
        return shutil.which(name)

    @staticmethod
    def _unix_bindable(path):
        """True when bind(2) on an AF_UNIX socket at `path` is permitted.

        AF_UNIX bind is denied on the OHOS HMDFS user volume (EPERM) but works
        on the app sandbox tmpfs, so the usable directory has to be probed at
        runtime instead of assumed.
        """
        try:
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        except (AttributeError, OSError):
            return False
        try:
            probe.bind(path)
            return True
        except OSError:
            return False
        finally:
            probe.close()
            try:
                os.unlink(path)
            except OSError:
                pass

    def _start_session_bus(self):
        """Start a private dbus-daemon on a unix socket; return (process, address).

        EXTERNAL auth is used (the same mechanism QtDBus implements) over a
        unix socket, so no TCP/ANONYMOUS workaround is needed. Returns
        (None, None) when no daemon/socket directory is usable.
        """
        daemon = self._dep_tool("dbus-daemon")
        if not daemon:
            self.output.warning("dbus-daemon not found in the dependency graph")
            return None, None

        # mkdtemp() creates a fresh owner-only directory atomically: a
        # pre-existing path or symlink cannot make the cleanup below remove
        # someone else's directory, and concurrent `conan create` runs never
        # share a socket.
        parents = []
        if self.settings.os == "OHOS":
            parents.append(("/data/storage/el2/base", ".mmqt-session-bus-"))
        parents.append((self.build_folder, ".mmqt-session-bus-"))
        parents.append((os.path.join(self.build_folder, "test-tmp"), ".mmqt-session-bus-"))

        for parent, prefix in parents:
            try:
                os.makedirs(parent, exist_ok=True)
                directory = tempfile.mkdtemp(prefix=prefix, dir=parent)
            except OSError:
                continue
            socket_path = os.path.join(directory, "bus.sock")
            if not self._unix_bindable(socket_path):
                self.output.info(f"AF_UNIX bind denied in {directory}; trying next candidate")
                shutil.rmtree(directory, ignore_errors=True)
                continue

            conf_path = os.path.join(directory, "session.conf")
            with open(conf_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    '<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"\n'
                    ' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n'
                    "<busconfig>\n"
                    "  <type>session</type>\n"
                    "  <keep_umask/>\n"
                    f"  <listen>unix:path={socket_path}</listen>\n"
                    "  <auth>EXTERNAL</auth>\n"
                    '  <policy context="default">\n'
                    '    <allow send_destination="*" eavesdrop="true"/>\n'
                    '    <allow eavesdrop="true"/>\n'
                    '    <allow own="*"/>\n'
                    "  </policy>\n"
                    "</busconfig>\n"
                )

            env = dict(os.environ)
            lib_dirs = [
                os.path.join(dep.package_folder, "lib")
                for dep in self.dependencies.build.values()
                if dep and dep.package_folder
            ]
            existing = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(p for p in lib_dirs + [existing] if p)
            shim = getattr(self, "_passwd_shim", None)
            if shim and os.path.isfile(shim):
                preload = env.get("LD_PRELOAD", "")
                env["LD_PRELOAD"] = shim + (os.pathsep + preload if preload else "")

            log_path = os.path.join(directory, "dbus-daemon.log")
            # The daemon inherits its own duplicate of the descriptor, so the
            # parent handle can be closed as soon as Popen() returns.
            with open(log_path, "w") as log_handle:
                process = subprocess.Popen(
                    [daemon, "--config-file=" + conf_path, "--print-address", "--nofork"],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
            address = None
            deadline = time.time() + 15
            while time.time() < deadline and process.poll() is None:
                try:
                    with open(log_path) as handle:
                        printed = handle.read().strip()
                except OSError:
                    printed = ""
                if printed:
                    lines = [line.strip() for line in printed.splitlines() if line.strip()]
                    # --print-address emits "unix:path=...,guid=..."; stderr is
                    # merged into the same log, so neither a warning line nor a
                    # partially flushed "unix:..." fragment may be taken as the
                    # address. Require both markers and skip everything else.
                    address = next(
                        (line for line in lines
                         if line.startswith("unix:") and "path=" in line),
                        None,
                    )
                    if address:
                        break
                time.sleep(0.2)
            if address:
                self.output.info(f"private session bus on {socket_path}: {address}")
                # Remembered so _run_upstream_tests() can remove the
                # per-run directory after the bus is stopped.
                self._session_bus_dir = directory
                return process, address
            self.output.warning(f"dbus-daemon failed to start in {directory}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
            shutil.rmtree(directory, ignore_errors=True)
        return None, None

    def _run_upstream_tests(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return
        if self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            self.output.info("tools.build:skip_test is set; upstream autotests skipped")
            return
        ctest = shutil.which("ctest") or "/data/service/hnp/bin/ctest"
        if not os.path.isfile(ctest):
            raise ConanException("ctest not found; cannot run the upstream autotests")

        test_env = self._library_runtime_env()
        # Qt6DBus dlopen()s libdbus-1.so.3 at runtime; the FEATURE_dbus=ON
        # qtbase binary has no NEEDED entry for it. The private-bus tool
        # package is the dbus build in the graph that ships the shared
        # library, so its lib dir belongs on the test LD_LIBRARY_PATH.
        bus_dep = self.dependencies.build.get("dbus")
        if bus_dep and bus_dep.package_folder:
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(bus_dep.package_folder, "lib")
            )
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        # /tmp is read-only on OHOS (E002): give the tools a writable tmpdir.
        tmpdir = os.path.join(self.build_folder, "test-tmp")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        for path in (tmpdir, test_home, xdg_runtime):
            os.makedirs(path, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("TMPDIR", tmpdir)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))

        bus_process = None
        try:
            bus_process, address = self._start_session_bus()
            if not address:
                raise ConanException(
                    "no usable session bus could be started; the upstream "
                    "autotests drive a FakeModem on the session bus and cannot run"
                )
            test_env.define("DBUS_SESSION_BUS_ADDRESS", address)

            # --timeout: a test that blocks on a missing session bus must fail
            # fast rather than hang the whole build.
            command = [
                ctest,
                "--test-dir",
                self.build_folder,
                # Multi-config generators need the configuration to test;
                # single-config generators ignore this option.
                "-C",
                str(self.settings.build_type),
                "--output-on-failure",
                "--no-tests=error",
                "--timeout",
                "120",
            ]
            with test_env.vars(self).apply():
                self.run(" ".join(shlex.quote(part) for part in command))
        finally:
            if bus_process is not None:
                bus_process.terminate()
                try:
                    bus_process.wait(timeout=5)
                except Exception:
                    bus_process.kill()
                bus_dir = getattr(self, "_session_bus_dir", "")
                if bus_dir:
                    shutil.rmtree(bus_dir, ignore_errors=True)

    # ── packaging ────────────────────────────────────────────────────────

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream installs a complete, relocatable KF6ModemManagerQtConfig.cmake
        # with find_dependency on Qt6Core/Qt6DBus. cmake_find_mode=none prevents
        # CMakeDeps from shadowing it with an incomplete generated config
        # (kconfig / kwindowsystem 6.26.0 precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", self._pc_name)
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = [self._pc_name]
        self.cpp_info.includedirs = [os.path.join("include", "KF6")]
        if self.options.shared:
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
