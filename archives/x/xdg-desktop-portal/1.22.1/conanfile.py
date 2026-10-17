#!/usr/bin/env python3
"""Conan recipe — xdg-desktop-portal 1.22.1 (Meson).

xdg-desktop-portal is the freedesktop portal service framework: a D-Bus
daemon (xdg-desktop-portal) that brokers desktop integration requests
(file chooser, open URI, screenshot, settings, ...) between sandboxed
apps and portal backend implementations. It does NOT link libflatpak
(flatpak is only one of its consumers) and does NOT produce libportal
(that is the separate libportal project, already in the registry).

Deliverables of this package (application):
  - libexec/xdg-desktop-portal                        (the portal daemon)
  - libexec/xdg-desktop-portal-validate-icon          (icon validation helper)
  - libexec/xdg-permission-store                      (permission store daemon)
  - share/dbus-1/interfaces/org.freedesktop.portal.*.xml  (portal interface XMLs)
  - share/dbus-1/services/*.service                   (D-Bus service files)
  - lib/systemd/user/*.service                        (systemd user units, data files)
  - lib/pkgconfig/xdg-desktop-portal.pc               (dataonly pc, interfaces_dir var)

OHOS adaptation (see patches/ + notes.md):
  - fuse3 / libpipewire / gstreamer-pbutils turned into meson feature
    options and disabled: none exist in the OHOS registry and all three only
    serve desktop-session backends (document portal FUSE mount, camera /
    screen-cast / remote-desktop portals, sound validation helper) that have
    no runtime on an OHOS PC anyway. Core daemon + interfaces are preserved.
  - glib build-time tools (gdbus-codegen, glib-mkenums, glib-compile-resources)
    are taken from the conan glib package: python tools get sh wrappers, the
    ELF tool gets a self-signed copy staged in the build tree plus an
    all-dependency LD_LIBRARY_PATH wrapper (aghermann 1.1.2 E511 pattern).
  - Installed ELF binaries are signed for OHOS exec (accountsservice pattern).
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class XdgDesktopPortalConan(ConanFile):
    name = "xdg-desktop-portal"
    version = "1.22.1"
    description = ("Desktop integration portal service framework "
                   "(D-Bus portal daemon + interface XMLs)")
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/flatpak/xdg-desktop-portal"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Dependency graph pinned to the glib/2.84.0.1 line: gdk-pixbuf/2.44.6
        # and json-glib/1.10.6 both require glib/2.84.0.1 (json-glib/1.6.6
        # pins glib/2.84.0 and would conflict — verified via conan graph).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("json-glib/1.10.6")
        self.requires("gdk-pixbuf/2.44.6")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xdg-desktop-portal {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ────────────────────────────────────────────────────────────────────
    # generate()
    # ────────────────────────────────────────────────────────────────────
    def generate(self):
        # Pin ar/as/strip/nm/ranlib by absolute path (CI worker exports
        # llvm-* names not on PATH) — xdg-dbus-proxy pattern.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {n: shutil.which(n) for n in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [n for n, p in tools.items() if p is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )

        # TMPDIR must be writable (HMDFS /tmp is read-only on OHOS workers)
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # hnp's ninja is a musl ELF whose NEEDED libc++_shared.so is only
        # provided by /system/lib64. The build profile carries only the
        # llvm/lib runtime path, and an inherited LD_LIBRARY_PATH can contain
        # malformed space-padded entries that shadow /system/lib64 — meson's
        # ninja detection subprocess then fails with exit 127 ("Could not
        # detect Ninja v1.8.2 or newer"). Prepend the system lib dir
        # explicitly (same treatment the local ohos-aarch64 profile applies
        # for binary-sign-tool's libc++ dependency; harmless on CI workers).
        if os.path.isdir("/system/lib64"):
            ld = os.environ.get("LD_LIBRARY_PATH", "")
            if not ld.split(":")[0] == "/system/lib64":
                os.environ["LD_LIBRARY_PATH"] = (
                    "/system/lib64" + (":" + ld if ld else "")
                )

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        # OHOS adaptation surface — everything that has no runtime here is
        # turned off; the OHOS portability patch makes fuse3/pipewire/
        # sound-validation real meson feature options.
        tc.project_options.update({
            "fuse3": "disabled",                       # no fuse3 in registry
            "pipewire": "disabled",                    # no libpipewire in registry
            "sound-validation": "disabled",            # no gstreamer-pbutils-1.0.pc
            "geoclue": "disabled",                     # no geoclue daemon
            "gudev": "disabled",                       # no udev
            "systemd": "disabled",                     # no libsystemd
            "flatpak-interfaces": "disabled",          # no flatpak dev files
            "tests": "enabled",                        # 0002 split: GTest unit binaries build standalone (glib only)
            "installed-tests": "false",
            "man-pages": "disabled",                   # no rst2man
            "documentation": "disabled",               # no sphinx
            "sandboxed-image-validation": "disabled",  # no bwrap
            "sandboxed-sound-validation": "disabled",  # no bwrap
        })
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        # meson resolves dependencies through pkg-config with the generators
        # folder on the search path; make that explicit for the configure
        # invocation as well (dconf pattern: buildenv injection is unreliable).
        cur = os.environ.get("PKG_CONFIG_PATH", "")
        if self.generators_folder not in cur.split(os.pathsep):
            os.environ["PKG_CONFIG_PATH"] = (
                self.generators_folder + (os.pathsep + cur if cur else "")
            )

        self._ensure_glib_pc_aliases()
        self._create_gio_unix_pc()
        self._patch_glib_pc_tool_variables()
        self._create_gdk_pixbuf_alias()

    # ── glib sub-package .pc files ──────────────────────────────────────
    def _ensure_glib_pc_aliases(self):
        """PkgConfigDeps only emits a .pc per declared component; synthesize
        the gio-2.0/gobject-2.0/gmodule-2.0/gthread-2.0 aliases from
        glib-2.0.pc when they are missing (evince pattern)."""
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        for filename, name in (
            ("gio-2.0.pc", "gio-2.0"),
            ("gobject-2.0.pc", "gobject-2.0"),
            ("gmodule-2.0.pc", "gmodule-2.0"),
            ("gthread-2.0.pc", "gthread-2.0"),
        ):
            alias_path = os.path.join(self.generators_folder, filename)
            if os.path.isfile(alias_path):
                continue
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _create_gio_unix_pc(self):
        """Create gio-unix-2.0.pc from gio-2.0.pc (xdg-dbus-proxy pattern):
        glib's recipe does not declare the gio-unix-2.0 pkg-config module,
        but meson's dependency('gio-unix-2.0') needs it (Cflags gains the
        gio-unix-2.0 include dir where gunixfdlist.h etc. live)."""
        gens = self.generators_folder
        gio_unix_pc = os.path.join(gens, "gio-unix-2.0.pc")
        gio_pc = os.path.join(gens, "gio-2.0.pc")
        if os.path.isfile(gio_unix_pc) or not os.path.isfile(gio_pc):
            return
        with open(gio_pc, encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.startswith("Name:"):
                new_lines.append("Name: gio-unix-2.0\n")
            elif line.startswith("Description:"):
                new_lines.append("Description: GIO Unix-specific APIs\n")
            elif line.startswith("Cflags:"):
                rest = line[len("Cflags:"):].rstrip("\n")
                new_lines.append(
                    "Cflags: -I${prefix}/include/gio-unix-2.0 " + rest + "\n"
                )
            else:
                new_lines.append(line)
        with open(gio_unix_pc, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    # ── glib build tools staging (evince pattern) ───────────────────────
    def _glib_package_folder(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                return dep.package_folder
        return None

    def _stage_glib_tool(self, name):
        """Expose a glib build tool from the conan glib package so meson's
        gnome module can execute it. Two flavors (evince 48.4 pattern,
        adapted):
        - python tools (gdbus-codegen, glib-mkenums) -> sh wrapper executing
          the host python with the original script path (hnp's glib-mkenums
          has a #!/usr/bin/perl shebang but /usr/bin/perl does not exist;
          the conan package scripts use /usr/bin/env python3)
        - ELF tools (glib-compile-resources) -> self-signed copy staged in
          the build tree + sh wrapper exporting every dependency's lib dir
          on LD_LIBRARY_PATH (aghermann 1.1.2 E511 pattern: some CI
          workers' HMDFS refuses to exec a cache-path ELF — meson reports
          the wrapper as code 126, which is what killed CI run 89577's
          resources generation. hnp's own glib-compile-resources lacks
          libffi.so.8, so the conan package binary is the base either way).
        """
        glib_folder = self._glib_package_folder()
        if not glib_folder:
            return None
        source = os.path.join(glib_folder, "bin", name)
        if not os.path.isfile(source):
            return None
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        os.makedirs(tools_dir, exist_ok=True)

        wrapper = os.path.join(tools_dir, name)
        python = shutil.which("python3") or "python3"
        quoted = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(source, "rb") as handle:
            first_line = handle.readline(128)
        if b"python" in first_line:
            body = "#!/bin/sh\nexec {} {} \"$@\"\n".format(quoted(python), quoted(source))
        else:
            # E511 (aghermann 1.1.2 pattern): some CI workers' HMDFS
            # refuses to exec an ELF straight from the conan cache (meson
            # reports the wrapper as code 126). Stage a self-signed copy
            # in the build tree: copy -> llvm-objcopy drops any stale
            # .codesign -> binary-sign-tool writes a fresh self-sign ->
            # exec the copy. Falls back to the cache path when the signing
            # tools are unavailable.
            staged = os.path.join(tools_dir, name + ".elf")
            real = source
            objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(objcopy) and os.path.isfile(signer):
                try:
                    shutil.copy2(source, staged)
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", staged],
                        check=False, capture_output=True,
                    )
                    signed = staged + ".signed"
                    subprocess.run(
                        [signer, "sign", "-inFile", staged,
                         "-outFile", signed, "-selfSign", "1"],
                        check=True, capture_output=True,
                    )
                    os.replace(signed, staged)
                    os.chmod(staged, 0o755)
                    real = staged
                except Exception as exc:
                    self.output.warning(
                        "glib tool self-sign failed for {}: {} "
                        "(fallback to cache path)".format(name, exc)
                    )
            # The tool's shared libs (libffi etc.) may resolve from any
            # dependency package, not glib alone (aghermann pattern).
            libdirs = []
            for _dep_name, dep in self.dependencies.items():
                lib = os.path.join(dep.package_folder or "", "lib")
                if os.path.isdir(lib) and lib not in libdirs:
                    libdirs.append(lib)
            glib_lib = os.path.join(glib_folder, "lib")
            if glib_lib not in libdirs:
                libdirs.append(glib_lib)
            body = ("#!/bin/sh\n"
                    "LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH exec {} \"$@\"\n"
                    .format(quoted(":".join(libdirs)), quoted(real)))
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        os.chmod(wrapper, 0o755)
        return wrapper

    def _patch_glib_pc_tool_variables(self):
        """Point the pkg-config tool variables of glib-2.0.pc / gio-2.0.pc at
        the staged wrappers. meson's gnome module resolves gdbus-codegen,
        glib-mkenums and glib-compile-resources through these variables
        (ModuleState.find_tool), and an unresolvable value aborts configure."""
        glib_tools = {
            "glib-2.0.pc": {
                "glib_mkenums": self._stage_glib_tool("glib-mkenums"),
                "glib_genmarshal": self._stage_glib_tool("glib-genmarshal"),
                "gobject_query": self._stage_glib_tool("gobject-query"),
            },
            "gio-2.0.pc": {
                "glib_compile_schemas": self._stage_glib_tool("glib-compile-schemas"),
                "glib_compile_resources": self._stage_glib_tool("glib-compile-resources"),
                "gdbus_codegen": self._stage_glib_tool("gdbus-codegen"),
            },
        }
        for pc_name, variables in glib_tools.items():
            pc_path = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_path):
                continue
            content = open(pc_path, encoding="utf-8").read()
            for variable, value in variables.items():
                if not value:
                    continue
                if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                    content = re.sub(
                        rf"^{re.escape(variable)}=.*$",
                        f"{variable}={value}",
                        content,
                        flags=re.M,
                    )
                else:
                    content = f"{variable}={value}\n" + content
            with open(pc_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _create_gdk_pixbuf_alias(self):
        """meson looks up gdk-pixbuf-2.0 while the conan package registers
        no pkg_config_name, so PkgConfigDeps emits gdk-pixbuf.pc only.
        Synthesize the -2.0 alias (same libs/includes)."""
        gens = self.generators_folder
        src = os.path.join(gens, "gdk-pixbuf.pc")
        dst = os.path.join(gens, "gdk-pixbuf-2.0.pc")
        if not os.path.isfile(src) or os.path.isfile(dst):
            return
        with open(src, encoding="utf-8") as source:
            content = source.read()
        content = re.sub(r"^Name:.*$", "Name: gdk-pixbuf-2.0", content, flags=re.M)
        with open(dst, "w", encoding="utf-8") as handle:
            handle.write(content)

    # ────────────────────────────────────────────────────────────────────
    # build / package
    # ────────────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if self.settings.os == "OHOS":
            self._run_upstream_unit_tests()

    def _run_upstream_unit_tests(self):
        """Run the upstream GTest C unit binaries (tests/ of the 1.22.1
        tarball) on the OHOS target itself. The 0002 gate split makes the
        three binaries (test-permission-db / test-xdp-utils /
        test-xdp-method-info) buildable with plain glib; they are executed
        directly from the meson build tree with the dependency libdirs on
        LD_LIBRARY_PATH and the G_TEST_* TAP variables that tests/meson.build
        normally injects.

        Skipped cases (explicit, per test):
          * test-permission-db /db/serialize — the test body hardcodes
            /tmp/test-permission-db-XXXXXX (mkstemp); the OHOS worker /
            target filesystem has a read-only /tmp (erofs), so the mkstemp
            call fails. Not portable by design (upstream never made the
            path overridable).
          * test-xdp-utils /app-id-via-systemd-unit — compiled out by the
            HAVE_LIBSYSTEMD guard (the OHOS build has -Dsystemd=disabled,
            libsystemd is not in the registry).
        """
        import glob

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        can_sign = os.path.isfile(objcopy) and os.path.isfile(signer)

        staged = os.path.join(self.build_folder, ".test-staged-libs")
        os.makedirs(staged, exist_ok=True)
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
                    dep.package_folder, rel)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
            fallback = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(fallback) and fallback not in libdirs:
                libdirs.append(fallback)

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
                if os.path.islink(src):
                    real = os.path.realpath(src)
                    if not os.path.isfile(real):
                        continue
                    src = real
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    continue
                os.chmod(dst, 0o755)
                if can_sign:
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

        # locate the three GTest binaries inside the meson build tree
        build_root = None
        for candidate in glob.glob(os.path.join(self.build_folder, "**",
                                                "build.ninja"), recursive=True):
            build_root = os.path.dirname(candidate)
            break
        assert build_root, "meson build.ninja not found under build folder"
        tests_src = os.path.join(self.source_folder, "tests")

        cases = [
            ("test-xdp-method-info", []),
            ("test-xdp-utils", []),
            # /db/serialize needs a writable /tmp (read-only on OHOS target)
            ("test-permission-db", ["-p", "/db/open", "-p", "/db/modify"]),
        ]
        libpath = os.pathsep.join([staged] + libdirs)
        passed = failed = 0
        for name, extra in cases:
            exe = None
            for cand in (os.path.join(build_root, name),
                         os.path.join(build_root, "tests", name)):
                if os.path.isfile(cand):
                    exe = cand
                    break
            assert exe, f"upstream unit test binary not found: {name}"
            if can_sign:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", exe],
                    check=False, capture_output=True)
                signed = exe + ".signed"
                subprocess.run(
                    [signer, "sign", "-inFile", exe, "-outFile", signed,
                     "-selfSign", "1"],
                    check=False, capture_output=True)
                if os.path.isfile(signed):
                    os.replace(signed, exe)
                    os.chmod(exe, 0o755)
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = (
                libpath + (os.pathsep + env["LD_LIBRARY_PATH"]
                           if env.get("LD_LIBRARY_PATH") else "")
            )
            env["G_TEST_SRCDIR"] = tests_src
            env["G_TEST_BUILDDIR"] = os.path.join(build_root, "tests")
            cmd = [exe] + extra
            self.output.info(f"RUN upstream unit test: {name} {' '.join(extra)}")
            proc = subprocess.run(cmd, env=env, capture_output=True,
                                  text=True, timeout=300, cwd=build_root)
            out = (proc.stdout or "") + (proc.stderr or "")
            for line in out.splitlines():
                if line.startswith(("TAP version", "1..", "ok ", "not ok ",
                                    "# ", "Ok", "FAIL", "PASS")):
                    self.output.info(f"[unit] {line}")
            if proc.returncode == 0:
                passed += 1
                self.output.info(f"[unit] {name}: PASS (rc=0)")
            else:
                failed += 1
                self.output.error(f"[unit] {name}: FAIL rc={proc.returncode}")
                self.output.error(out[-2000:])
        if failed:
            raise Exception(
                f"upstream GTest unit tests failed: {failed} binary/binaries "
                f"returned non-zero ({passed} passed)")
        self.output.info(
            f"[unit] upstream GTest unit binaries: {passed} PASSED, "
            f"{failed} failed (serialize skipped: read-only /tmp; "
            "systemd case compiled out: -Dsystemd=disabled)")

    def package(self):
        meson = Meson(self)
        meson.install()
        self._fix_installed_pc()
        self._sign_installed_elfs()

    def _fix_installed_pc(self):
        """The dataonly xdg-desktop-portal.pc is generated with prefix=/
        (meson install prefix), which makes interfaces_dir an absolute
        system path that never exists. Rewrite prefix to the relocatable
        ${pcfiledir}/../.. form so pkg-config resolves it against the
        package folder (pc lives at share/pkgconfig/)."""
        pc = os.path.join(
            self.package_folder, "share", "pkgconfig", "xdg-desktop-portal.pc"
        )
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("prefix=/\n", "prefix=${pcfiledir}/../..\n", 1)
        content = content.replace(
            "datarootdir=/share\n", "datarootdir=${prefix}/share\n", 1
        )
        with open(pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _sign_installed_elfs(self):
        """OHOS requires the .codesign section to exec installed ELF
        binaries (accountsservice/evince pattern: objcopy removes any stale
        section first, then binary-sign-tool writes a fresh self-sign via
        a separate output file that atomically replaces the original). The
        daemon is exec'ed by the CI smoke test (--version)."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                "xdg-desktop-portal: OHOS signing tools not found, "
                "installed binaries are left unsigned"
            )
            return
        import glob
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "libexec", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so*"),
        ):
            targets.extend(
                p for p in glob.glob(pattern, recursive=True)
                if os.path.isfile(p) and not os.path.islink(p)
            )
        for target in targets:
            with open(target, "rb") as handle:
                magic = handle.read(4)
            if magic != b"\x7fELF":
                continue
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", target],
                check=False, capture_output=True,
            )
            signed = target + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", target, "-outFile", signed,
                 "-selfSign", "1"],
                check=False, capture_output=True,
            )
            if os.path.isfile(signed):
                os.replace(signed, target)
            os.chmod(target, 0o755)

    def package_info(self):
        # Application package: no public C library, no headers. The binaries
        # land in bin/ (conan MesonToolchain maps libexecdir to bin).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "xdg-desktop-portal")
        # Transitive link closure so consumers (and VirtualRunEnv in
        # test_package) get the runtime library path of every dependency.
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "json-glib::json-glib-1.0",
            "gdk-pixbuf::gdk-pixbuf",
        ]
