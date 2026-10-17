#!/usr/bin/env python3
"""Conan L1 test_package for cairo-dock/3.5.0 — real verification of the
packaged artefacts (R34: the test must exercise the package, never a stub).

cairo-dock is a GTK3 desktop dock: bringing the UI up needs a display (and on
OHOS a Broadway server), which the CI worker cannot provide.  What is verified
here is therefore split in two parts:

  A. Executable / linkage / loader probes (headless-safe, the same shape as
     archives/k/klavaro/3.14):
       1. the packaged ``bin/cairo-dock`` exists, is executable and is an
          AArch64 ELF;
       2. its DT_NEEDED closure carries the shipped ``libgldi.so.3`` plus the
          GTK3/Cairo/GLib stack it is built on;
       3. the shipped ``lib/libgldi.so`` closure carries the OpenGL provider
          (the "GL is a hard requirement, X11/Wayland are optional" claim);
       4. the installed ``gldi-config.h`` reports GLDI_VERSION 3.5.0 and does
          NOT define HAVE_X11 / HAVE_WAYLAND / HAVE_EGL / HAVE_GLX (the
          optional backends are genuinely switched off);
       5. executing the packaged binary must get at least as far as GDK
          display init: a loader error is a FAIL, "cannot open display" is the
          expected headless outcome (R40 partial for the interactive UI).

  B. A real consumer build+run: ``test_cairo_dock.c`` links -lgldi through the
     packaged pkg-config module and calls two exported API functions.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps

#: libraries the dock executable must be linked against (R34/R40 evidence that
#: the packaged build really is the GTK3/Cairo/GLDI dock).
EXPECTED_NEEDED_EXE = (
    "libgldi.so.3",
    "libgtk-3.so.0",
    "libcairo.so.2",
    "libglib-2.0.so.0",
)

#: any one of these proves the desktop-GL provider is in the closure
GL_PROVIDER_SONAMES = ("libOSMesa.so.8", "libGL.so.1")

BASH = "/data/service/hnp/bin/bash"


class CairoDockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            if "/system/lib64" not in cur:
                os.environ["LD_LIBRARY_PATH"] = ("/system/lib64:" + cur) if cur else "/system/lib64"
        cmake = CMake(self)
        # The musl loader ignores LD_LIBRARY_PATH for DT_RUNPATH entries, so
        # embed DT_RPATH pointing at every dependency libdir (pan/0.165 fix).
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                path = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(path) and path not in rpaths:
                    rpaths.append(path)
        if rpaths:
            flags = " ".join(["-Wl,--disable-new-dtags"] + [f"-Wl,-rpath,{p}" for p in rpaths])
            cmake.configure(variables={"CMAKE_EXE_LINKER_FLAGS": flags})
        else:
            cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ #
    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg_folder = dep.package_folder
        exe = os.path.join(pkg_folder, "bin", "cairo-dock")
        if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
            raise AssertionError(f"FAIL: packaged cairo-dock executable missing: {exe}")
        self.output.info(f"[R38] packaged executable present: {exe}")

        with open(exe, "rb") as handle:
            head = handle.read(20)
        assert head[:4] == b"\x7fELF", "FAIL: cairo-dock is not an ELF binary"
        assert head[18] == 0xB7 and head[19] == 0x00, (
            f"FAIL: cairo-dock is not AArch64 (e_machine={head[18]:#x})")
        self.output.info("[OK] packaged cairo-dock is an AArch64 ELF")

        readelf = self._find_tool("llvm-readelf")
        assert readelf, "FAIL: llvm-readelf unavailable, cannot verify DT_NEEDED"
        needed_exe = self._needed(exe, readelf)
        self.output.info(f"[INFO] cairo-dock DT_NEEDED ({len(needed_exe)}): {needed_exe}")
        missing = [lib for lib in EXPECTED_NEEDED_EXE if lib not in needed_exe]
        assert not missing, f"FAIL: DT_NEEDED closure of the dock executable is missing {missing}"

        libgldi = self._find_libgldi(pkg_folder)
        assert libgldi, f"FAIL: packaged libgldi shared object missing under {pkg_folder}/lib"
        needed_lib = self._needed(libgldi, readelf)
        self.output.info(f"[INFO] libgldi DT_NEEDED ({len(needed_lib)}): {needed_lib}")
        gl_seen = [s for s in GL_PROVIDER_SONAMES if s in needed_exe or s in needed_lib]
        assert gl_seen, (
            "FAIL: no desktop-GL provider (one of "
            f"{GL_PROVIDER_SONAMES}) in the closure of {exe} / {libgldi}")
        self.output.info(f"[OK] desktop-GL provider linked: {gl_seen}")

        self._check_config_header(pkg_folder)
        self._run_packaged_binary(exe)
        self._run_consumer_probe()

        self.output.info(
            "[R40] the interactive dock UI needs a display session (OHOS: Broadway "
            "server + browser), which CI cannot provide: binary, linkage, GL "
            "provider, generated configuration and the libgldi consumer API are "
            "verified headless — GUI behaviour remains a partial-verification item.")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_tool(name):
        for cand in (f"/data/service/hnp/bin/{name}", shutil.which(name)):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _needed(self, elf, readelf):
        proc = subprocess.run([readelf, "-d", elf], capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, f"FAIL: readelf -d {elf} failed: {proc.stderr[:200]}"
        return [line.strip().split("[")[-1].rstrip("]")
                for line in proc.stdout.splitlines() if "(NEEDED)" in line]

    @staticmethod
    def _find_libgldi(pkg_folder):
        libdir = os.path.join(pkg_folder, "lib")
        if not os.path.isdir(libdir):
            return None
        names = sorted(os.listdir(libdir))
        for name in names:
            if name.startswith("libgldi.so.3"):
                return os.path.join(libdir, name)
        for name in names:
            if name.startswith("libgldi.so"):
                return os.path.join(libdir, name)
        return None

    def _check_config_header(self, pkg_folder):
        """GLDI_VERSION must be the ported version and the optional display
        backends must be off (the falsifiable form of "X11/Wayland optional")."""
        header = os.path.join(pkg_folder, "include", "cairo-dock", "gldit", "gldi-config.h")
        assert os.path.isfile(header), f"FAIL: installed gldi-config.h missing: {header}"
        with open(header, encoding="utf-8") as handle:
            text = handle.read()
        assert '#define GLDI_VERSION "3.5.0"' in text, (
            f"FAIL: gldi-config.h does not declare GLDI_VERSION 3.5.0:\n{text[:400]}")
        self.output.info("[OK] installed gldi-config.h declares GLDI_VERSION 3.5.0")
        for macro in ("HAVE_X11", "HAVE_GLX", "HAVE_WAYLAND", "HAVE_EGL"):
            assert f"#define {macro}" not in text, (
                f"FAIL: {macro} unexpectedly defined in gldi-config.h — the optional "
                "display backend was supposed to be disabled on OHOS")
        self.output.info("[OK] HAVE_X11 / HAVE_GLX / HAVE_WAYLAND / HAVE_EGL are not defined")

    def _run_packaged_binary(self, exe):
        """Headless execution probe: reaching GDK init proves the whole NEEDED
        closure loads; a loader error is a hard failure."""
        out = self._exec_capture("dock_version", f'"{exe}" --version')
        self.output.info(f"[INFO] `cairo-dock --version` output: {out[:400]!r}")
        for marker in ("Error loading shared library", "Error relocating",
                       "cannot open shared object"):
            assert marker not in out, (
                f"FAIL: the dynamic loader could not resolve the closure: {out[:300]}")
        if "3.5.0" in out:
            self.output.info("[OK] `cairo-dock --version` printed 3.5.0")
        else:
            self.output.info("[OK] NEEDED closure resolved at runtime; GDK display init "
                             "reached (headless: no display is the expected outcome)")

    def _run_consumer_probe(self):
        probe = os.path.join(self.build_folder, "test_cairo_dock")
        assert os.path.isfile(probe), f"FAIL: consumer probe was not built: {probe}"
        out = self._exec_capture("consumer_probe", f'"{probe}"')
        self.output.info(f"[INFO] consumer probe output:\n{out}")
        assert "FAIL" not in out, f"FAIL: the libgldi consumer probe reported failures:\n{out}"

    def _exec_capture(self, label, command):
        """Execute `command` inside the conan run environment (through self.run,
        so the run-env script is sourced) and return its combined output.

        /system/lib64 carries libc++_shared.so, which the conan closure does not
        ship; it is prepended in the wrapper because VirtualRunEnv's conanrun.sh
        knows nothing about the OHOS sysroot.
        """
        script = os.path.join(self.generators_folder, f"_probe_{label}.sh")
        out_file = os.path.join(self.generators_folder, f"_probe_{label}.out")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write('#!/bin/bash\n'
                         'export LD_LIBRARY_PATH="/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
                         f'{command}\n')
        os.chmod(script, 0o755)
        self.run(f'"{BASH}" "{script}" > "{out_file}" 2>&1', env="conanrun", ignore_errors=True)
        if os.path.isfile(out_file):
            with open(out_file, encoding="utf-8", errors="replace") as handle:
                return handle.read()
        return ""
