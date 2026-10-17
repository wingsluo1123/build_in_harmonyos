#!/usr/bin/env python3
"""Consumer test for the signond daemon package.

Three groups, all against the *installed* package:

  CASE 1  real daemon binary startup path (HarmonyOS host): bin/signond is
          executed and must reach the session-bus probe, where it stops with
          the upstream `qFatal("SignonDaemon requires DBus to start working")`.
          This sandbox has no D-Bus session bus (no dbus-daemon binary, and
          binding a Unix socket is EPERM on every writable mount), so that
          abort is the expected terminal state; the assertion is on the
          qFatal marker plus exit status 134 (SIGABRT).  The D-Bus service
          registration and the AuthService/Identity/AuthSession interfaces are
          NOT exercised here (no bus available); see reports/test-report.md.
  CASE 2  authentication end-to-end through the packaged plugin host: the C++
          consumer spawns bin/signonpluginprocess, loads libpasswordplugin.so
          from the packaged plugin directory and completes two auth flows over
          the packaged blob IPC protocol (see consumer.cpp).
  CASE 3  artifact contract: every declared artifact is present and the daemon
          ELF has no private build-cache path baked into DT_NEEDED/RUNPATH.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SignondTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    _libs = ("libsignon-plugins", "libsignon-plugins-common", "libsignon-extension")

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6 provider (Core/DBus/Sql/Xml/Network) for the consumer build.
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase-sql-dbus is built with cmake_find_mode=none, so CMakeDeps
        # generates no config/targets for it, yet signond's generated config
        # find_dependency()s it and its link interface references its target.
        # Map it onto Qt's real config/target (Qt6_DIR points at the
        # qtbase-sql-dbus package), the same way the libsignon-qt 8.61
        # test_package maps its qtbase dependency.
        deps = CMakeDeps(self)
        deps.set_property("qtbase-sql-dbus", "cmake_file_name", "Qt6")
        deps.set_property("qtbase-sql-dbus", "cmake_target_name", "Qt6::Core")
        deps.generate()

        qtbase = self.dependencies["qtbase-sql-dbus"]
        qt6_dir = os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6")
        if not os.path.isdir(qt6_dir):
            raise ConanException(
                "qtbase-sql-dbus does not provide lib/cmake/Qt6 at {}".format(
                    qtbase.package_folder)
            )

        tc = CMakeToolchain(self)
        tc.variables["Qt6_DIR"] = qt6_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ test
    def test(self):
        package_folder = self.dependencies["signond"].package_folder
        self._test_daemon_startup(package_folder)
        self._test_plugin_host_e2e(package_folder)
        self._test_artifact_contract(package_folder)

    # --- CASE 1 -------------------------------------------------------------
    def _test_daemon_startup(self, package_folder):
        signond = os.path.join(package_folder, "bin", "signond")
        self._require(os.path.isfile(signond), "CASE 1: bin/signond is installed")

        log = os.path.join(self.build_folder, "signond-startup.log")
        if os.path.exists(log):
            os.remove(log)
        storage = os.path.join(self.build_folder, "signond-storage")
        os.makedirs(storage, exist_ok=True)

        # SSO_LOGGING_OUTPUT=stdout switches signond's syslog message handler
        # back to stderr so the startup trace is observable.
        command = (
            'SSO_LOGGING_OUTPUT=stdout SSO_STORAGE_PATH="{}" '
            '"{}" > "{}" 2>&1; echo "EXIT=$?" >> "{}"'
        ).format(storage, signond, log, log)
        self.run(command, env="conanrun")

        with open(log, "r", encoding="utf-8", errors="replace") as stream:
            output = stream.read()
        self.output.info("signond startup output:\n{}".format(output))

        self._require(
            "SignonDaemon requires DBus to start working" in output,
            "CASE 1: daemon loaded its configuration and reached the session-bus "
            "probe (qFatal); D-Bus service registration and the credentials DB "
            "open are not exercised on this platform",
        )
        self._require(
            "EXIT=134" in output,
            "CASE 1: daemon stops through the upstream qFatal path (SIGABRT/134)",
        )

    # --- CASE 2 -------------------------------------------------------------
    def _test_plugin_host_e2e(self, package_folder):
        consumer = os.path.join(self.cpp.build.bindir, "signond_consumer")
        self._require(os.path.isfile(consumer),
                      "CASE 2: consumer binary was built")
        plugin_process = os.path.join(package_folder, "bin", "signonpluginprocess")
        plugins_dir = os.path.join(package_folder, "lib", "signon")
        self.run('"{}" "{}" "{}"'.format(consumer, plugin_process, plugins_dir),
                 env="conanrun")

    # --- CASE 3 -------------------------------------------------------------
    def _test_artifact_contract(self, package_folder):
        required = [
            "bin/signond",
            "bin/signonpluginprocess",
            "lib/signon/libpasswordplugin.so",
            "lib/signon/libexampleplugin.so",
            "lib/pkgconfig/signond.pc",
            "lib/pkgconfig/signon-plugins.pc",
            "lib/pkgconfig/signon-plugins-common.pc",
            "lib/pkgconfig/SignOnExtension.pc",
            "include/signond/signoncommon.h",
            "include/signon-plugins/SignOn/authpluginif.h",
            "include/signon-plugins/SignOn/blobiohandler.h",
            "include/signon-plugins/SignOn/ipc.h",
            # Client types the plugin SDK headers include; shipped here so the
            # SDK is self-contained (libsignon-qt stays a separate package).
            "include/signon-plugins/SignOn/sessiondata.h",
            "include/signon-plugins/SignOn/signonerror.h",
            "include/signon-plugins/SignOn/SessionData",
            "include/signon-extension/SignOn/extension-interface.h",
            "share/dbus-1/services/com.google.code.AccountsSSO.SingleSignOn.service",
            "share/signond/signond.conf",
        ]
        # The shared/static option decides the library suffix.
        for name in self._libs:
            if not self._exists_with_any_suffix(os.path.join(package_folder, "lib"), name):
                raise ConanException(
                    "CASE 3: missing packaged library {} in lib/".format(name))

        missing = [rel for rel in required
                   if not os.path.exists(os.path.join(package_folder, rel))]
        self._require(not missing,
                      "CASE 3: declared artifacts installed ({})".format(missing or "all"))

        # The L5a CI gate requires DT_SONAME on every linkable shared library
        # in lib/ (upstream's qmake build never sets VERSION, so upstream .so
        # files have none and downstream linkers cannot address them by
        # soname; the CMake build adds them).
        for name in self._libs:
            soname = self._soname(os.path.join(package_folder, "lib", name + ".so"))
            if soname is not None:
                self._require(soname,
                              "CASE 3: {} carries DT_SONAME".format(name))

        # No private build-cache path may be baked into the daemon ELF.
        self._test_no_private_paths(os.path.join(package_folder, "bin", "signond"))

    def _test_no_private_paths(self, binary):
        reader = shutil.which("readelf") or shutil.which("llvm-readelf")
        if not reader:
            self.output.warning("CASE 3: readelf unavailable; ELF path check skipped")
            return
        log = os.path.join(self.build_folder, "signond-readelf.log")
        self.run('"{}" -d "{}" > "{}" 2>&1'.format(reader, binary, log))
        with open(log, "r", encoding="utf-8", errors="replace") as stream:
            dynamic = stream.read()
        leaked = [line.strip() for line in dynamic.splitlines()
                  if ("NEEDED" in line or "RPATH" in line or "RUNPATH" in line)
                  and ("/storage/" in line or ".conan2" in line)]
        self._require(not leaked,
                      "CASE 3: no conan cache path in DT_NEEDED/RUNPATH ({})".format(
                          leaked or "clean"))
        for symbol in ("libQt6Sql.so.6", "libQt6DBus.so.6", "libsignon-extension.so",
                       "libsignon-plugins-common.so"):
            self._require(symbol in dynamic,
                          "CASE 3: daemon links {}".format(symbol))

    # --- helpers ------------------------------------------------------------
    def _soname(self, library):
        """Return the DT_SONAME of `library`, or None when it is not a shared
        library / no ELF reader is available (static builds)."""
        if not os.path.exists(library):
            return None
        reader = shutil.which("readelf") or shutil.which("llvm-readelf")
        if not reader:
            self.output.warning("CASE 3: readelf unavailable; SONAME check skipped")
            return None
        log = os.path.join(self.build_folder, "soname.log")
        self.run('"{}" -d "{}" > "{}" 2>&1'.format(reader, library, log))
        with open(log, "r", encoding="utf-8", errors="replace") as stream:
            dynamic = stream.read()
        for line in dynamic.splitlines():
            if "SONAME" in line and "[" in line:
                value = line.split("[", 1)[1].split("]", 1)[0].strip()
                if value and not value.startswith("/"):
                    return value
        return ""

    @staticmethod
    def _exists_with_any_suffix(directory, name):
        return any(os.path.exists(os.path.join(directory, name + suffix))
                   for suffix in (".so", ".a", ".dylib"))

    @staticmethod
    def _require(condition, message):
        if not condition:
            raise ConanException("[test_package] {}".format(message))
        return True
