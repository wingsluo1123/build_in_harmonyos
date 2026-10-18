#!/usr/bin/env python3
"""Conan test_package for profiled 1.0.13.

8 个具名用例：5 个 libprofile API 功能用例（test_libprofile.c）+
3 个鸿蒙专用用例（ELF 架构 / profile.pc 版本 / 真实 D-Bus 会话总线往返）。
"""
import os
import struct
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class ProfiledTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ utils
    def _pkg_dir(self, name):
        return self.dependencies[name].package_folder

    def _case(self, name, ok, detail=""):
        self.output.info(f"[CASE] {name}: {'PASS' if ok else 'FAIL'}"
                         + (f" -- {detail}" if detail else ""))
        if not ok:
            raise ConanException(f"test case failed: {name} ({detail})")

    @staticmethod
    def _elf_header(path):
        with open(path, "rb") as fh:
            head = fh.read(20)
        if head[:4] != b"\x7fELF":
            return None
        # EI_CLASS: 2 = ELFCLASS64 ; e_machine at 18..20 (little endian)
        return head[4], struct.unpack("<H", head[18:20])[0]

    # ------------------------------------------------------------------ cases
    def _case_pc_version(self):
        """鸿蒙适配点：VERS 从 changelog 的 1.0.12 覆盖为包版本。"""
        version = self.dependencies["profiled"].ref.version
        pc = os.path.join(self._pkg_dir("profiled"), "lib", "pkgconfig", "profile.pc")
        with open(pc, "r") as fh:
            text = fh.read()
        self._case("ohos_profile_pc_version", f"Version: {version}" in text,
                   f"profile.pc Version == {version}")

    def _case_elf(self):
        """鸿蒙专用：产物必须是 ELF64 + AArch64（OHOS）。"""
        pkg = self._pkg_dir("profiled")
        targets = ["bin/profiled", "bin/profileclient", "bin/profile-tracker",
                   "lib/libprofile.so.0", "lib/libprofile.a"]
        bad = []
        for rel in targets:
            path = os.path.join(pkg, rel)
            if not os.path.isfile(path):
                bad.append(f"{rel}:missing")
                continue
            if rel.endswith(".a"):
                continue                      # archive, not an ELF object
            hdr = self._elf_header(path)
            if hdr is None or hdr[0] != 2 or hdr[1] != 183:
                bad.append(f"{rel}:{hdr}")
        self._case("ohos_elf_aarch64", not bad,
                   "ELF64/EM_AARCH64" if not bad else ",".join(bad))

    def _case_roundtrip(self):
        """鸿蒙专用：自建 D-Bus 会话总线（TCP）+ 拉起 profiled，跑消费方往返。"""
        pkg = self._pkg_dir("profiled")
        dbus_pkg = self._pkg_dir("dbus")
        dbus_daemon = os.path.join(dbus_pkg, "bin", "dbus-daemon")
        dbus_send = os.path.join(dbus_pkg, "bin", "dbus-send")
        profiled_bin = os.path.join(pkg, "bin", "profiled")
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_libprofile")

        libdirs = [os.path.join(pkg, "lib"),
                   os.path.join(self._pkg_dir("glib"), "lib"),
                   os.path.join(self._pkg_dir("expat"), "lib")]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + [os.environ.get("LD_LIBRARY_PATH", "")])

        home = os.path.join(self.build_folder, "test-home")
        os.makedirs(os.path.join(home, ".profiled"), exist_ok=True)
        os.environ["HOME"] = home

        conf = os.path.join(self.build_folder, "session-tcp.conf")
        with open(conf, "w") as fh:
            fh.write(
                '<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"\n'
                ' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n'
                "<busconfig>\n"
                "  <type>session</type>\n"
                "  <keep_umask/>\n"
                "  <listen>tcp:host=127.0.0.1,port=0</listen>\n"
                "  <auth>ANONYMOUS</auth>\n"
                "  <allow_anonymous/>\n"
                '  <policy context="default">\n'
                '    <allow send_destination="*" eavesdrop="true"/>\n'
                '    <allow eavesdrop="true"/>\n'
                '    <allow own="*"/>\n'
                "  </policy>\n"
                "</busconfig>\n")

        bus_log = os.path.join(self.build_folder, "dbus-daemon.log")
        prof_log = os.path.join(self.build_folder, "profiled.log")
        bus = subprocess.Popen(
            [dbus_daemon, "--config-file=" + conf, "--print-address", "--nofork"],
            stdout=open(bus_log, "w"), stderr=subprocess.STDOUT, env=os.environ)
        prof = None
        try:
            address = None
            deadline = time.time() + 20
            while time.time() < deadline and bus.poll() is None:
                try:
                    with open(bus_log) as fh:
                        line = fh.readline().strip()
                except OSError:
                    line = ""
                if line.startswith("tcp:"):
                    address = line
                    break
                time.sleep(0.2)
            if not address:
                raise ConanException("dbus-daemon did not publish a session address")
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = address
            self.output.info(f"session bus: {address}")

            prof = subprocess.Popen(
                [profiled_bin], stdout=open(prof_log, "w"),
                stderr=subprocess.STDOUT, env=os.environ)

            # 等待 com.nokia.profiled 注册到会话总线
            names = ""
            deadline = time.time() + 20
            while time.time() < deadline:
                r = subprocess.run(
                    [dbus_send, "--session", "--dest=org.freedesktop.DBus",
                     "--type=method_call", "--print-reply", "/",
                     "org.freedesktop.DBus.ListNames"],
                    capture_output=True, text=True, env=os.environ)
                names = r.stdout or ""
                if "com.nokia.profiled" in names:
                    break
                if prof.poll() is not None:
                    raise ConanException(
                        f"profiled exited early (rc={prof.returncode}): "
                        + open(prof_log).read()[:400])
                time.sleep(0.3)
            self._case("ohos_dbus_session_roundtrip",
                       "com.nokia.profiled" in names,
                       "com.nokia.profiled registered on session bus")

            self.run(f'"{test_bin}"', env="conanrun")
        finally:
            for proc in (prof, bus):
                if proc is None:
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

    def test(self):
        self._case_pc_version()
        self._case_elf()
        if str(self.settings.os) != "OHOS":
            self.output.warning("non-OHOS host: skipping live D-Bus round-trip")
            return
        self._case_roundtrip()
