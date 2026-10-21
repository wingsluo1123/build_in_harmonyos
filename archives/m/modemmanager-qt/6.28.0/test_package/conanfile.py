#!/usr/bin/env python3
"""Conan test_package for modemmanager-qt 6.28.0.

L1 consumer test: links KF6::ModemManagerQt from the installed package and
exercises the real public API (notifier(), modemDevices(), Modem::uni(),
Modem::isValid(), D-Bus service lifecycle signals).

The shared library talks to org.freedesktop.ModemManager1 on the *system*
bus (src/manager.cpp, non-MMQT_STATIC path); Qt honours
DBUS_SYSTEM_BUS_ADDRESS, so a private dbus-daemon started on a unix socket
serves as both the session and the system bus for this test. The socket must
live where bind(2) on AF_UNIX is permitted: the OHOS HMDFS user volume
rejects it, the app sandbox tmpfs (/data/storage/el2/base) accepts it.
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


# Same test-only account shim as the recipe: the OHOS sandbox UID has no
# /etc/passwd or /etc/group entry, and dbus-daemon rejects EXTERNAL clients it
# cannot map to a user. Preloading this library gives the daemon a synthetic
# entry for the current UID only; no system file is modified.
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


class ModemmanagerQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly required so its package folder is available for the
        # CMakeDeps prefix path setup (the installed
        # KF6ModemManagerQtConfig.cmake does find_dependency(Qt6Core/Qt6DBus)).
        self.requires("qtbase/6.11.1.1")

    def build_requirements(self):
        # dbus/1.14.10.3 (shared-client-library revision) ships both the
        # daemon and the libdbus-1.so.3 that Qt6DBus dlopen()s at runtime.
        self.tool_requires("dbus/1.14.10.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg and pkg.package_folder:
            pkg_folder = pkg.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_folder}/lib/cmake")')
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _compiler_candidates(self):
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
        directory = os.path.join(self.build_folder, "passwd-shim")
        os.makedirs(directory, exist_ok=True)
        source_path = os.path.join(directory, "passwd_shim.c")
        with open(source_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_PASSWD_SHIM_C)
        library_path = os.path.join(directory, "passwd_shim.so")

        errors = []
        for compiler in self._compiler_candidates():
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
                    return library_path
                errors.append(f"{compiler}: produced a non-AArch64 ELF")
                continue
            detail = (completed.stderr or completed.stdout or "").strip()
            errors.append(f"{compiler}: rc={completed.returncode} {detail[:400]}")
        raise ConanException(
            "could not build the passwd shim required by dbus-daemon:\n" + "\n".join(errors)
        )

    @staticmethod
    def _bindable(path):
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

    def _start_bus(self):
        dep = self.dependencies.build.get("dbus")
        if not dep or not dep.package_folder:
            raise ConanException("dbus build requirement (dbus-daemon) is unavailable")
        daemon = os.path.join(dep.package_folder, "bin", "dbus-daemon")
        if not os.path.isfile(daemon):
            raise ConanException(f"dbus-daemon not found at {daemon}")

        # mkdtemp() creates a fresh owner-only directory atomically: a
        # pre-existing path or symlink cannot make the cleanup below remove
        # someone else's directory, and concurrent `conan create` runs never
        # share a socket.
        parents = []
        if self.settings.os == "OHOS":
            parents.append(("/data/storage/el2/base", ".mmqt-tp-bus-"))
        parents.append((self.build_folder, ".mmqt-tp-bus-"))
        shim = self._build_passwd_shim() if self.settings.os == "OHOS" else None

        for parent, prefix in parents:
            try:
                os.makedirs(parent, exist_ok=True)
                directory = tempfile.mkdtemp(prefix=prefix, dir=parent)
            except OSError:
                continue
            socket_path = os.path.join(directory, "bus.sock")
            if not self._bindable(socket_path):
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
            log_path = os.path.join(directory, "dbus-daemon.log")
            env = dict(os.environ)
            # dbus-daemon is dynamically linked; give it the lib dirs of the
            # whole build context (libdbus-1, libexpat, ...).
            lib_dirs = [
                os.path.join(d.package_folder, "lib")
                for d in self.dependencies.build.values()
                if d and d.package_folder
            ]
            existing = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                p for p in lib_dirs + [existing] if p
            )
            if shim:
                preload = env.get("LD_PRELOAD", "")
                env["LD_PRELOAD"] = shim + (os.pathsep + preload if preload else "")
            # The daemon inherits its own duplicate of the descriptor, so the
            # parent handle can be closed as soon as Popen() returns.
            with open(log_path, "w") as log_handle:
                process = subprocess.Popen(
                    [daemon, "--config-file=" + conf_path, "--print-address", "--nofork"],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
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
                        # Remembered so test() can remove the per-run
                        # directory after the bus is stopped.
                        self._bus_dir = directory
                        return process, address
                time.sleep(0.2)
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
            shutil.rmtree(directory, ignore_errors=True)
        raise ConanException("could not start a private dbus-daemon for the consumer test")

    def test(self):
        bus_process, address = self._start_bus()
        try:
            env = Environment()
            lib_dirs = [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ]
            dbus_dep = self.dependencies.build.get("dbus")
            if dbus_dep and dbus_dep.package_folder:
                lib_dirs.append(os.path.join(dbus_dep.package_folder, "lib"))
            if self.settings.os == "OHOS":
                lib_dirs.append("/system/lib64")
                import glob as _glob
                lib_dirs.extend(sorted(_glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )))
            env.prepend_path("LD_LIBRARY_PATH", lib_dirs)
            env.define("DBUS_SESSION_BUS_ADDRESS", address)
            # The shared library uses QDBusConnection::systemBus(); Qt reads
            # DBUS_SYSTEM_BUS_ADDRESS before falling back to
            # /var/run/dbus/system_bus_socket.
            env.define("DBUS_SYSTEM_BUS_ADDRESS", address)
            env.define("QT_QPA_PLATFORM", "offscreen")
            tmpdir = os.path.join(self.build_folder, "test-tmp")
            test_home = os.path.join(self.build_folder, "test-home")
            runtime_dir = os.path.join(self.build_folder, "xdg-runtime")
            for path in (tmpdir, test_home, runtime_dir):
                os.makedirs(path, exist_ok=True)
            os.chmod(runtime_dir, 0o700)
            env.define("TMPDIR", tmpdir)
            env.define("HOME", test_home)
            env.define("XDG_RUNTIME_DIR", runtime_dir)

            with env.vars(self).apply():
                cmake = CMake(self)
                cmake.test()
                self.run(shlex.quote(
                    os.path.join(self.cpp.build.bindirs[0], "test_modemmanagerqt")
                ))
        finally:
            bus_process.terminate()
            try:
                bus_process.wait(timeout=5)
            except Exception:
                bus_process.kill()
            bus_dir = getattr(self, "_bus_dir", "")
            if bus_dir:
                shutil.rmtree(bus_dir, ignore_errors=True)
