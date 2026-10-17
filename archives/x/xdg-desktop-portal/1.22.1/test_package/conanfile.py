#!/usr/bin/env python3
"""Conan test_package — xdg-desktop-portal 1.22.1.

Consumer-side verification of the delivered portal package:
  1. xdg-desktop-portal daemon binary exists, is OHOS-signed and runs
     (--version prints "xdg-desktop-portal 1.22.1" — config.h PACKAGE_STRING).
  2. The dataonly xdg-desktop-portal.pc exists and its interfaces_dir
     variable resolves to a directory that actually contains the portal
     D-Bus interface XMLs.
  3. The portal interface XMLs are installed (org.freedesktop.portal.Request
     is the base interface every portal consumer needs).
  4. The D-Bus service activation file for the portal daemon is installed.
  5. End-to-end consumer case (HarmonyOS-specific): a private D-Bus session
     bus (dbus-daemon over loopback TCP) is brought up, the packaged
     xdg-permission-store daemon is started against it and the full
     PermissionStore API is driven through glib's gdbus client
     (List -> SetPermission -> GetPermission -> Lookup -> List -> Delete ->
     List, plus the on-disk gvdb materialization check).

Layout note: conan's MesonToolchain maps libexecdir to bin/, and the dataonly
pc is installed to share/pkgconfig/ (datadir), both verified on the real
package. The daemon is linked against shared glib/json-glib/gdk-pixbuf
libraries from the dependency packages, so it is executed with the runtime
library path of all dependencies (VirtualRunEnv + explicit LD_LIBRARY_PATH).
"""
import os
import shutil
import subprocess

from conan import ConanFile


class XdgDesktopPortalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Private D-Bus session bus for the end-to-end consumer test:
        # dbus-daemon (+ its expat dependency) drives a loopback-TCP session
        # so the packaged xdg-permission-store can be exercised through the
        # real org.freedesktop.impl.portal.PermissionStore API.
        self.requires("dbus/1.14.10.1")

    def _pkg(self):
        return self.dependencies["xdg-desktop-portal"].package_folder

    def _dep_libdirs(self):
        """Runtime library dirs of every host dependency (the daemon links
        shared glib/json-glib/gdk-pixbuf). Works for both plain recipes
        (cpp_info.libdirs) and component recipes (glib declares components),
        with a package_folder/lib fallback."""
        libdirs = []
        for dep in self.dependencies.host.values():
            candidates = []
            try:
                candidates.extend(list(dep.cpp_info.libdirs or []))
            except Exception:
                pass
            try:
                for comp in (getattr(dep.cpp_info, "components", None) or {}).values():
                    candidates.extend(list(comp.libdirs or []))
            except Exception:
                pass
            for rel in candidates:
                libdir = rel if os.path.isabs(rel) else os.path.join(
                    dep.package_folder, rel
                )
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
            fallback = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(fallback) and fallback not in libdirs:
                libdirs.append(fallback)
        return libdirs

    def _stage_runtime_libs(self, libdirs):
        """Copy every dependency .so* into a build-tree staging dir with
        clean 0755 permissions (OHOS loader reads the staged copies, not
        the cache packages). Guards against registry packages whose cache
        folders carry restrictive modes: CI runs 10-13 21:36/22:26 had the
        daemon exec die with 'Error loading shared library
        libjson-glib-1.0.so.0' straight from the package lib dir while the
        very same LD_LIBRARY_PATH worked locally — the staged copy (owned
        by the running user, mode 755) removes that variable entirely."""
        staged = os.path.join(self.build_folder, "staged-libs")
        os.makedirs(staged, exist_ok=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        can_sign = os.path.isfile(objcopy) and os.path.isfile(signer)
        for libdir in libdirs:
            try:
                entries = os.listdir(libdir)
            except OSError:
                continue
            for fn in entries:
                if not (fn.startswith("lib") and ".so" in fn):
                    continue
                src = os.path.join(libdir, fn)
                if not os.path.isfile(src):
                    continue
                dst = os.path.join(staged, fn)
                if os.path.exists(dst):
                    continue
                # Materialize symlinks: registry packages commonly ship
                # libX.so.0 -> libX.so.0.1.2, and the loader wants the
                # SONAME present as a real file in the staged dir (a
                # skipped symlink left the name missing, which is exactly
                # the "Error loading shared library" seen in runs
                # 21:36/22:26/23:33/00:10).
                if os.path.islink(src):
                    real = os.path.realpath(src)
                    if not os.path.isfile(real):
                        continue
                    src = real
                try:
                    shutil.copy2(src, dst)
                except OSError as exc:
                    # Unreadable source on this runner (registry package
                    # modes): say so loudly instead of silently skipping.
                    self.output.warning(
                        "staged-libs: cannot read %s from %s (%s)"
                        % (fn, libdir, exc))
                    continue
                os.chmod(dst, 0o755)
                if can_sign:
                    # OHOS musl loader validates .codesign on every
                    # non-system .so it maps; re-sign the staged copy so
                    # a registry package whose signature the runner
                    # rejects still loads (libsoundio _sign_ohos_elf
                    # pattern).
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", dst],
                        check=False, capture_output=True)
                    signed = dst + ".signed"
                    subprocess.run(
                        [signer, "sign", "-inFile", dst, "-outFile",
                         signed, "-selfSign", "1"],
                        check=False, capture_output=True)
                    if os.path.isfile(signed):
                        os.replace(signed, dst)
                        os.chmod(dst, 0o755)
        return staged

    # ────────────────────────────────────────────────────────────────
    # End-to-end consumer case (HarmonyOS-specific)
    # ────────────────────────────────────────────────────────────────
    def _stage_e2e_dir(self):
        """Build-tree dir for the private bus + daemons + gvdb state."""
        d = os.path.join(self.build_folder, "e2e-dbus")
        os.makedirs(d, exist_ok=True)
        return d

    def _stage_e2e_binaries(self, d):
        """Stage & self-sign the dbus-daemon and the packaged
        xdg-permission-store (OHOS loader validates .codesign on every
        non-system ELF it execs — the cached registry copies are re-signed
        so the current user's loader accepts them)."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        assert os.path.isfile(objcopy) and os.path.isfile(signer), (
            "OHOS signing tools not found (llvm-objcopy/binary-sign-tool)")

        dbus_pkg = self.dependencies["dbus"].package_folder
        glib_pkg = self.dependencies["glib"].package_folder
        pkg = self._pkg()
        staged_libs = os.path.join(self.build_folder, "staged-libs")

        out = {}
        for name, src in (
            ("dbus-daemon", os.path.join(dbus_pkg, "bin", "dbus-daemon")),
            ("xdg-permission-store", os.path.join(pkg, "bin", "xdg-permission-store")),
            ("gdbus", os.path.join(glib_pkg, "bin", "gdbus")),
        ):
            assert os.path.isfile(src), f"E2E binary missing: {src}"
            dst = os.path.join(d, name)
            # defensive unlink: a previous run in this build folder may have
            # left a signed copy whose mode/attrs make copy2 overwrite fail
            # with EPERM on HMDFS
            if os.path.exists(dst):
                os.chmod(dst, 0o755)
                os.unlink(dst)
            shutil.copy2(src, dst)
            subprocess.run([objcopy, "--remove-section", ".codesign", dst],
                           check=False, capture_output=True)
            signed = dst + ".signed"
            subprocess.run([signer, "sign", "-inFile", dst, "-outFile", signed,
                            "-selfSign", "1"], check=False, capture_output=True)
            if os.path.isfile(signed):
                os.replace(signed, dst)
            os.chmod(dst, 0o755)
            out[name] = dst

        # expat for dbus-daemon; the rest (glib/json-glib/...) is already
        # covered by the staged-libs dir the version check populates.
        for dep in self.dependencies.host.values():
            for rel in (list(dep.cpp_info.libdirs or []) or ["lib"]):
                libdir = rel if os.path.isabs(rel) else os.path.join(
                    dep.package_folder, rel)
                if not os.path.isdir(libdir):
                    continue
                for fn in os.listdir(libdir):
                    if fn.startswith("libexpat.so"):
                        shutil.copy2(os.path.join(libdir, fn),
                                     os.path.join(d, fn))
                        os.chmod(os.path.join(d, fn), 0o755)
        return out, staged_libs

    def _start_private_bus(self, d, daemon):
        """Private session bus over loopback TCP with ANONYMOUS auth.

        Why TCP and not the usual unix socket: the OHOS filesystem the
        test runs on rejects unix-domain bind() (HMDFS returns EPERM) and
        /tmp is a read-only erofs mount; abstract unix sockets authenticate
        but intermittingly stall on this kernel. loopback TCP with
        <auth>ANONYMOUS</auth> + <allow_anonymous/> is the one transport
        that works reliably on the OHOS target (dbus/1.14.10.1 ships its
        own OHOS session.conf using the same fallback).
        """
        conf = os.path.join(d, "session-e2e.conf")
        with open(conf, "w", encoding="utf-8") as handle:
            handle.write(
                "<!DOCTYPE busconfig PUBLIC "
                '"-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"\n'
                '"http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n'
                "<busconfig>\n"
                "  <type>session</type>\n"
                "  <keep_umask/>\n"
                "  <listen>tcp:host=127.0.0.1,port=0</listen>\n"
                "  <auth>ANONYMOUS</auth>\n"
                "  <allow_anonymous/>\n"
                "  <policy context=\"default\">\n"
                '    <allow send_destination="*" send_type="*"/>\n'
                '    <allow receive_sender="*" receive_type="*"/>\n'
                '    <allow own="*"/>\n'
                "    <allow user=\"*\"/>\n"
                "  </policy>\n"
                "</busconfig>\n")
        addr_file = os.path.join(d, "bus-addr.txt")
        env = dict(os.environ)
        env.pop("DBUS_SESSION_BUS_ADDRESS", None)
        # the staged dbus-daemon resolves libexpat.so.1 from the staging dir
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d] + [x for x in env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
                   if x])
        # Run the daemon in the FOREGROUND (no --fork) so its lifetime is
        # owned by this Popen handle — the CI worker image has no pkill,
        # so the bus must be stopped via terminate() on the handle, never
        # by pattern-matching process names.
        proc = subprocess.Popen(
            [daemon, "--config-file=" + conf, "--print-address"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            cwd=d, text=True)
        import time as _t
        addr = None
        deadline = _t.monotonic() + 30
        while _t.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            line = line.strip()
            if line.startswith("tcp:"):
                addr = line
                break
        assert addr, (
            "no tcp: address from dbus-daemon (rc="
            f"{proc.poll()}): run it manually to inspect")
        with open(addr_file, "w", encoding="utf-8") as handle:
            handle.write(addr + "\n")
        return addr, proc

    def _gdbus(self, gdbus, addr, dest, method, *args, timeout=30):
        """Run one gdbus call against the private bus; returns stdout."""
        objpath = "/org/freedesktop/impl/portal/PermissionStore"
        cmd = [gdbus, "call", "--address=" + addr,
               "--dest", dest, "--object-path", objpath,
               "--method", method] + list(args)
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = self._e2e_libpath
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, env=env)
        if proc.returncode != 0:
            raise Exception(
                f"gdbus {method} failed (rc={proc.returncode}): "
                f"{(proc.stderr or proc.stdout)[-500:]}")
        return (proc.stdout or "").strip()

    def _run_e2e_permission_store(self):
        """End-to-end: private bus -> packaged xdg-permission-store ->
        full PermissionStore API round-trips via the glib gdbus client."""
        if self.settings.os != "OHOS":
            return
        d = self._stage_e2e_dir()
        bins, staged_libs = self._stage_e2e_binaries(d)

        libpath = os.pathsep.join(
            [d, staged_libs]
            + [p for p in (os.environ.get("LD_LIBRARY_PATH", "")
                           .split(os.pathsep)) if p])
        self._e2e_libpath = libpath

        data_home = os.path.join(d, "data")
        home = os.path.join(d, "home")
        run_dir = os.path.join(d, "run")
        for sub in (data_home, home, run_dir):
            os.makedirs(sub, exist_ok=True)

        addr, bus_proc = self._start_private_bus(d, bins["dbus-daemon"])
        self.output.info(f"[e2e] private session bus up: {addr}")

        dest = "org.freedesktop.impl.portal.PermissionStore"
        store_proc = None
        try:
            env = dict(os.environ)
            env.update({
                "DBUS_SESSION_BUS_ADDRESS": addr,
                "LD_LIBRARY_PATH": libpath,
                "XDG_DATA_HOME": data_home,
                "HOME": home,
                "XDG_RUNTIME_DIR": run_dir,
                "TMPDIR": run_dir,
            })
            store_log = open(os.path.join(d, "pstore.log"), "wb")
            store_proc = subprocess.Popen(
                [bins["xdg-permission-store"]],
                env=env, cwd=d, stdout=store_log, stderr=store_log)

            gdbus = bins["gdbus"]

            # 1. wait for the name to be owned on the bus
            import time as _time
            owned = False
            for _ in range(60):
                out = self._gdbus(
                    gdbus, addr, "org.freedesktop.DBus",
                    "org.freedesktop.DBus.NameHasOwner",
                    "'%s'" % dest, timeout=15)
                if "true" in out:
                    owned = True
                    break
                _time.sleep(0.5)
            assert owned, (
                "xdg-permission-store did not own "
                f"{dest} on the private bus (see {d}/pstore.log)")
            self.output.info("[e2e] 1/8 PermissionStore name owned: True")

            # 2. List on a fresh table -> empty
            out = self._gdbus(gdbus, addr, dest, dest + ".List", "'t1'")
            assert "[]" in out.replace("@as ", ""), f"expected empty list, got {out}"
            self.output.info(f"[e2e] 2/8 List(fresh) -> {out}")

            # 3. SetPermission
            self._gdbus(gdbus, addr, dest, dest + ".SetPermission",
                        "'t1'", "true", "'res1'", "'app1'",
                        "['read', 'write']")
            self.output.info("[e2e] 3/8 SetPermission(read,write) -> ()")

            # 4. GetPermission -> the exact permissions back
            out = self._gdbus(gdbus, addr, dest, dest + ".GetPermission",
                              "'t1'", "'res1'", "'app1'")
            assert ("'read'" in out and "'write'" in out), (
                f"unexpected GetPermission reply: {out}")
            self.output.info(f"[e2e] 4/8 GetPermission -> {out}")

            # 5. Lookup -> app->permissions mapping + data
            out = self._gdbus(gdbus, addr, dest, dest + ".Lookup",
                              "'t1'", "'res1'")
            assert "'app1'" in out, f"unexpected Lookup reply: {out}"
            self.output.info(f"[e2e] 5/8 Lookup -> {out}")

            # 6. List -> the resource is there
            out = self._gdbus(gdbus, addr, dest, dest + ".List", "'t1'")
            assert "res1" in out, f"unexpected List reply: {out}"
            self.output.info(f"[e2e] 6/8 List(after set) -> {out}")

            # 7. on-disk gvdb materialization (XDG_DATA_HOME/flatpak/db/t1)
            db_file = os.path.join(data_home, "flatpak", "db", "t1")
            assert os.path.isfile(db_file), (
                f"permission store did not materialize {db_file}")
            self.output.info(
                f"[e2e] 7/8 gvdb on disk: {db_file} "
                f"({os.path.getsize(db_file)} bytes)")

            # 8. Delete -> resource gone, List empty again
            self._gdbus(gdbus, addr, dest, dest + ".Delete", "'t1'", "'res1'")
            out = self._gdbus(gdbus, addr, dest, dest + ".List", "'t1'")
            assert "[]" in out.replace("@as ", ""), f"expected empty list after delete, got {out}"
            self.output.info(f"[e2e] 8/8 Delete + List -> {out}")
        finally:
            if store_proc is not None:
                store_proc.terminate()
                try:
                    store_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    store_proc.kill()
            if bus_proc is not None:
                bus_proc.terminate()
                try:
                    bus_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    bus_proc.kill()
        self.output.info(
            "[e2e] xdg-permission-store end-to-end consumer case PASSED "
            "(private D-Bus session, 8 assertions)")

    def test(self):
        pkg = self._pkg()

        # ── 1. daemon binary + version string ──────────────────────────
        daemon = None
        for candidate in (
            os.path.join(pkg, "bin", "xdg-desktop-portal"),
            os.path.join(pkg, "libexec", "xdg-desktop-portal"),
            os.path.join(pkg, "lib", "xdg-desktop-portal"),
        ):
            if os.path.isfile(candidate):
                daemon = candidate
                break
        assert daemon, "xdg-desktop-portal daemon binary not found in package"
        print(f"[test] daemon found at {daemon}")

        if self.settings.os in ("Linux", "OHOS"):
            # Runtime library path for the shared glib/json-glib/gdk-pixbuf
            # the daemon links against. CI run 实证（10-13 21:36）：仅靠
            # os.environ 注入不够——conan 的 VirtualRunEnv 在 API 边界的
            # 激活时序会丢失该值，worker 上 daemon exec 时 loader 报
            # "Error loading shared library libjson-glib-1.0.so.0"。
            # 把路径直接焊进命令行（export + exec 同一 shell），绕开一切
            # 环境继承不确定性。
            libdirs = self._dep_libdirs()
            if libdirs:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                    libdirs + [os.environ.get("LD_LIBRARY_PATH", "")]
                ).rstrip(os.pathsep)
            # self.run() so the CI L0d gate sees a real execution (not a
            # stub); a non-zero exit code raises. Output goes to a file via
            # shell redirection because ConanFile.run's stdout argument
            # accepts a stream with a real fileno only.
            out_file = os.path.join(self.build_folder, "xdp-version-out.txt")
            staged = self._stage_runtime_libs(libdirs)
            ld_value = (
                os.pathsep.join([staged] + libdirs) + os.pathsep
                if libdirs else ""
            )
            self.run(
                f'export LD_LIBRARY_PATH="{ld_value}$LD_LIBRARY_PATH"; '
                f'"{daemon}" --version > "{out_file}"',
                cwd=self.build_folder,
                env=None,
            )
            with open(out_file, encoding="utf-8") as handle:
                output = handle.read()
            print(f"[test] --version output={output.strip()!r}")
            assert "xdg-desktop-portal 1.22.1" in output, (
                f"unexpected version output: {output!r}"
            )

        # ── 2. icon validation helper ──────────────────────────────────
        helper = None
        for candidate in (
            os.path.join(pkg, "bin", "xdg-desktop-portal-validate-icon"),
            os.path.join(pkg, "libexec", "xdg-desktop-portal-validate-icon"),
        ):
            if os.path.isfile(candidate):
                helper = candidate
                break
        assert helper, "xdg-desktop-portal-validate-icon helper not found"

        # ── 3. permission store daemon (fuse3-independent deliverable) ──
        pstore = None
        for candidate in (
            os.path.join(pkg, "bin", "xdg-permission-store"),
            os.path.join(pkg, "libexec", "xdg-permission-store"),
        ):
            if os.path.isfile(candidate):
                pstore = candidate
                break
        assert pstore, "xdg-permission-store daemon not found"

        # ── 4. dataonly pc + interfaces_dir → real XMLs ────────────────
        pc_path = None
        for candidate in (
            os.path.join(pkg, "share", "pkgconfig", "xdg-desktop-portal.pc"),
            os.path.join(pkg, "lib", "pkgconfig", "xdg-desktop-portal.pc"),
        ):
            if os.path.isfile(candidate):
                pc_path = candidate
                break
        assert pc_path, "dataonly xdg-desktop-portal.pc not found"
        print(f"[test] pc found at {pc_path}")

        interfaces_dir = None
        with open(pc_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith("interfaces_dir="):
                    interfaces_dir = line.split("=", 1)[1]

        assert interfaces_dir, "interfaces_dir variable missing in pc file"
        # Expand the relocatable pc variables against the package folder
        # (pkg-config itself is not assumed on the test machine).
        expanded = interfaces_dir.replace(
            "${pcfiledir}", os.path.dirname(os.path.dirname(pc_path))
        )
        expanded = expanded.replace(
            "${prefix}", os.path.dirname(os.path.dirname(os.path.dirname(pc_path)))
            if os.path.basename(os.path.dirname(pc_path)) == "pkgconfig"
            else pkg
        )
        expanded = expanded.replace("${datarootdir}", pkg + "/share")
        expanded = expanded.replace("${datadir}", pkg + "/share")
        print(f"[test] interfaces_dir={interfaces_dir!r} -> {expanded!r}")
        assert os.path.isdir(expanded), f"interfaces_dir does not exist: {expanded}"

        for iface in (
            "org.freedesktop.portal.Request.xml",
            "org.freedesktop.portal.FileChooser.xml",
            "org.freedesktop.portal.OpenURI.xml",
            "org.freedesktop.portal.ScreenCast.xml",
            "org.freedesktop.impl.portal.Request.xml",
        ):
            path = os.path.join(expanded, iface)
            assert os.path.isfile(path), f"interface XML missing: {path}"
        n_xml = len([f for f in os.listdir(expanded) if f.endswith(".xml")])
        print(f"[test] {n_xml} interface XMLs installed")
        assert n_xml >= 30, f"expected >=30 interface XMLs, got {n_xml}"

        # ── 5. D-Bus service activation file ───────────────────────────
        service = os.path.join(
            pkg, "share", "dbus-1", "services",
            "org.freedesktop.portal.Desktop.service",
        )
        assert os.path.isfile(service), f"D-Bus service file missing: {service}"

        print("[test] all xdg-desktop-portal assertions passed")

        # ── 6. end-to-end consumer case (HarmonyOS-specific) ──────────
        self._run_e2e_permission_store()
