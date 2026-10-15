import glob
import os
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class DbusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("c") or compilers.get("cc")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        # Both entries must pass: the consumer flow (one connection routed
        # through a daemon back to itself) and the HarmonyOS-specific
        # multi-process integration test (daemon + separate service process +
        # separate client processes over a pathname AF_UNIX socket).  Any
        # failure raises via self.run(..., ignore_errors=False).
        self._consumer_flow()
        self._hos_multiproc_test()

    def _consumer_flow(self):
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_dbus",
        )
        # r07：dbus 引入 glib 依赖后，test_dbus 运行时需加载
        # libglib-2.0/libgobject-2.0/libgio-2.0 等共享库
        # （libdbus 客户端库已透传依赖），把 glib 库目录写入 os.environ，
        # 否则 "Error loading shared library libgirepository-2.0.so.0" 启动失败。
        # r09：expat 对齐 2.8.2.1 后同样需要注入 expat 库路径（libexpat.so.1）。
        # 注：Conan 2 self.run() 的 env 参数须为列表而非 dict，故直接改 os.environ。
        glib_pkg = self.dependencies["glib"].package_folder
        glib_libdir = os.path.join(glib_pkg, "lib")
        expat_pkg = self.dependencies["expat"].package_folder
        expat_libdir = os.path.join(expat_pkg, "lib")
        os.environ["LD_LIBRARY_PATH"] = (
            glib_libdir + os.pathsep + expat_libdir + os.pathsep
            + os.environ.get("LD_LIBRARY_PATH", "")
        )
        if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            self.run(test_bin, ignore_errors=False)
            return

        # 否则尝试用包内 dbus-daemon 自启动一个 TCP 会话总线并完成往返：
        # OHOS 沙箱可能禁止 AF_UNIX bind，TCP 是等价可运行路径。
        dbus_pkg = self.dependencies["dbus"].package_folder
        daemon = os.path.join(dbus_pkg, "bin", "dbus-daemon")
        if not os.path.isfile(daemon):
            self.output.warning("dbus-daemon not in package; running client-only test")
            self.run(test_bin, ignore_errors=False)
            return

        conf = os.path.join(self.build_folder, "session-tcp.conf")
        with open(conf, "w") as f:
            f.write(
                '<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"\n'
                ' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n'
                "<busconfig>\n"
                "  <type>session</type>\n"
                "  <keep_umask/>\n"
                "  <listen>tcp:host=127.0.0.1,port=0</listen>\n"
                "  <auth>ANONYMOUS</auth>\n"
                "  <allow_anonymous/>\n"
                "  <policy context=\"default\">\n"
                '    <allow send_destination="*" eavesdrop="true"/>\n'
                '    <allow eavesdrop="true"/>\n'
                '    <allow own="*"/>\n'
                "  </policy>\n"
                "</busconfig>\n"
            )
        # The client library is shared in this version, so the consumer needs
        # the package's lib directory on the loader path. Without it the run
        # dies before the test code:
        #   Error loading shared library libdbus-1.so.3: (needed by ./test_dbus)
        dep = self.dependencies["dbus"]
        libdirs = [os.path.join(dep.package_folder, d)
                   for d in (dep.cpp_info.libdirs or ["lib"])]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in libdirs if os.path.isdir(d)]
            + [os.environ.get("LD_LIBRARY_PATH", "")]
        ).strip(os.pathsep)

        log_path = os.path.join(self.build_folder, "dbus-daemon.log")
        daemon_proc = subprocess.Popen(
            [daemon, "--config-file=" + conf, "--print-address", "--nofork"],
            stdout=open(log_path, "w"),
            stderr=subprocess.STDOUT,
            env=os.environ,
        )
        try:
            address = None
            deadline = time.time() + 10
            while time.time() < deadline and daemon_proc.poll() is None:
                try:
                    with open(log_path, "r") as lf:
                        line = lf.readline()
                        if line and line.startswith("tcp:"):
                            address = line.strip()
                            break
                except OSError:
                    pass
                time.sleep(0.2)
            if address:
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = address
                self.output.info(f"started dbus-daemon at {address}")
                # 在 daemon 存活期间运行消费方测试（真实会话总线往返）
                self.run(test_bin, ignore_errors=False)
            else:
                self.output.warning("dbus-daemon did not print address; running client-only test")
                self.run(test_bin, ignore_errors=False)
        finally:
            daemon_proc.terminate()
            try:
                daemon_proc.wait(timeout=3)
            except Exception:
                daemon_proc.kill()

    def _find_multiproc_binary(self, name):
        """Locate a built test binary; returns None when it is missing."""
        dirs = list(self.cpp.build.bindirs or [])
        if self.cpp.build.libdirs:
            dirs += list(self.cpp.build.libdirs)
        for d in dirs:
            cand = os.path.join(d, name)
            if os.path.isfile(cand):
                return cand
        hits = glob.glob(
            os.path.join(self.build_folder, "**", name), recursive=True
        )
        return hits[0] if hits else None

    def _hos_multiproc_test(self):
        """HarmonyOS-specific multi-process integration test — mandatory.

        Runs the packaged dbus-daemon on a pathname AF_UNIX socket in a
        sandbox directory this run probes, plus a separate service process
        and separate client processes (own PIDs, own connections); see
        test_package/dbus_hos_multiproc.c for the full chain.  Missing
        binary or any failed step fails the package test — never a silent
        skip and never a green result without the chain actually running.
        """
        exe = self._find_multiproc_binary("dbus_hos_multiproc")
        if exe is None:
            raise ConanException(
                "dbus_hos_multiproc was not built; the HarmonyOS "
                "multi-process integration test must run"
            )
        dbus_pkg = self.dependencies["dbus"].package_folder
        os.environ["HOS_DBUS_DAEMON"] = os.path.join(
            dbus_pkg, "bin", "dbus-daemon"
        )
        # The SHARED libdbus-1 must be loadable by every child process; make
        # sure the package lib dir is on the loader path regardless of which
        # branch _consumer_flow() took.
        dep = self.dependencies["dbus"]
        libdirs = [
            os.path.join(dep.package_folder, d)
            for d in (dep.cpp_info.libdirs or ["lib"])
        ]
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in libdirs if os.path.isdir(d)] + [existing]
        ).strip(os.pathsep)
        # getpwuid/getpwuid_r shim for dbus-daemon only: this image's sandbox
        # uid (20020101) has no /etc/passwd entry, and the daemon resolves
        # the passwd entry while completing EXTERNAL authentication — without
        # it every EXTERNAL connection is dropped and clients time out.
        # (Scope verified on device: the client side does not need the shim.)
        shim = self._find_multiproc_binary("libhos_nopw.so")
        if shim:
            os.environ["HOS_DBUS_PW_SHIM"] = shim
            self.output.info(f"dbus-daemon passwd shim (test harness): {shim}")
        else:
            self.output.warning(
                "libhos_nopw.so not built — dbus-daemon may fail to "
                "complete EXTERNAL auth on this image; the test will say so"
            )
        self.output.info(f"running HarmonyOS multi-process test: {exe}")
        self.run(exe, ignore_errors=False)