#!/usr/bin/env python3
"""Conan recipe for lxi-tools 2.8 (Meson)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LxiToolsConan(ConanFile):
    name = "lxi-tools"
    version = "2.8"
    description = "LXI command-line and GTK4 tools for network test instruments"
    license = "BSD-3-Clause"
    homepage = "https://github.com/lxi-tools/lxi-tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lxi", "scpi", "instrumentation", "gtk4")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lxi-tools is validated for Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("liblxi/1.22")
        self.requires("lua/5.4.8.1")
        self.requires("readline/8.3")
        self.requires("gtk4/4.22.4")
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("libadwaita/1.2.0")
        self.requires("gtksourceview5/5.22.0")
        self.requires("json-glib/1.10.6.1")
        self.requires("cairo/1.18.4")
        self.requires("gdk-pixbuf/2.44.6")
        self.requires("harfbuzz/14.2.0.1.1.1", override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("pango/1.56.4", override=True)
        self.requires("zstd/1.5.7.1", override=True)

    def build_requirements(self):
        # Upstream conditionally registers its desktop metadata test when this
        # validator is present.  Use the published OHOS tool instead of
        # silently reducing the upstream test denominator.
        self.tool_requires("desktop-file-utils/0.28")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        pkg_config = shutil.which("pkg-config")
        if not pkg_config:
            raise ConanInvalidConfiguration("pkg-config is required to resolve Conan dependencies")
        # Meson does not infer a native pkg-config executable for an unknown
        # cross target such as HarmonyOS.  Keep dependency resolution on the
        # build machine while PkgConfigDeps supplies target-only .pc files.
        toolchain.binaries["pkg-config"] = pkg_config
        for meson_name, executable_name in (("ar", "llvm-ar"), ("strip", "llvm-strip")):
            executable = shutil.which(executable_name)
            if executable:
                toolchain.binaries[meson_name] = executable
        toolchain.project_options["gui"] = True
        toolchain.project_options["bashcompletiondir"] = "share/bash-completion/completions"
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["b_lundef"] = False
        for folder in (self.source_folder, self.build_folder):
            mapped = "/usr/src/lxi-tools-2.8"
            toolchain.c_args.extend(
                [f"-ffile-prefix-map={folder}={mapped}", f"-fmacro-prefix-map={folder}={mapped}"]
            )
        self._configure_glib_resource_tool(toolchain)
        toolchain.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _configure_glib_resource_tool(self, toolchain):
        tool = shutil.which("glib-compile-resources")
        if not tool and not cross_building(self):
            glib = self.dependencies.get("glib")
            if glib and glib.package_folder:
                candidate = os.path.join(glib.package_folder, "bin", "glib-compile-resources")
                if os.path.isfile(candidate):
                    tool = candidate
                    self.buildenv_info.prepend_path("PATH", os.path.dirname(candidate))
                    self.runenv_info.prepend_path("PATH", os.path.dirname(candidate))
        if not tool:
            raise ConanInvalidConfiguration("glib-compile-resources is required for the default GUI")

        probe_env = os.environ.copy()
        runtime = self._glib_resource_runtime()
        if runtime:
            current = probe_env.get("LD_LIBRARY_PATH")
            probe_env["LD_LIBRARY_PATH"] = runtime + ((os.pathsep + current) if current else "")
        help_result = subprocess.run(
            [tool, "--help"], capture_output=True, text=True, env=probe_env, check=False
        )
        if "--dependency-file" not in help_result.stdout + help_result.stderr:
            wrapper = Path(self.generators_folder) / "glib_compile_resources_compat.py"
            wrapper.write_text(
                """import subprocess
import sys
from pathlib import Path

tool = {!r}
args = []
depfile = None
i = 1
while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == "--dependency-file" and i + 1 < len(sys.argv):
        depfile = sys.argv[i + 1]
        i += 2
        continue
    if arg.startswith("--dependency-file="):
        depfile = arg.split("=", 1)[1]
        i += 1
        continue
    args.append(arg)
    i += 1
result = subprocess.run([tool] + args, check=False)
if result.returncode == 0 and depfile:
    Path(depfile).touch()
raise SystemExit(result.returncode)
""".format(tool),
                encoding="utf-8",
            )
            toolchain.binaries["glib-compile-resources"] = [sys.executable, str(wrapper)]

        pc_file = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(pc_file):
            raise ConanException("PkgConfigDeps did not generate gio-2.0.pc")
        text = Path(pc_file).read_text(encoding="utf-8")
        assignment = f"glib_compile_resources={tool}\n"
        if "glib_compile_resources=" not in text:
            Path(pc_file).write_text(assignment + text, encoding="utf-8")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        helper_env = Environment()
        resource_runtime = self._glib_resource_runtime()
        if resource_runtime:
            helper_env.prepend_path("LD_LIBRARY_PATH", resource_runtime)
        # Build helpers (notably glib-compile-resources on native OHOS) can
        # have their own runtime closure.  Conan's generated build environment
        # must cover Meson's configure, compile and test subprocesses too.
        with VirtualBuildEnv(self).vars().apply():
            with helper_env.vars(self).apply():
                meson.configure()
                meson.build()
                if can_run(self):
                    meson.test()

    @staticmethod
    def _glib_resource_runtime():
        tool = shutil.which("glib-compile-resources")
        if not tool or not str(tool).startswith("/data/service/hnp/"):
            return None
        # HarmonyOS places its native GLib helper and libffi runtime in
        # sibling HNP prefixes.  This build-only path is never packaged.
        hnp_root = Path(tool).parent.parent
        runtimes = sorted(hnp_root.glob("libffi.org/*/lib/libffi.so.8"))
        return str(runtimes[-1].parent) if runtimes else None

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            for name in ("lxi", "lxi-gui"):
                self._sign_elf(os.path.join(self.package_folder, "bin", name))

    def _tool_candidates(self, name):
        executable = shutil.which(name)
        if executable:
            yield executable
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = compilers.get("c") if compilers else None
        if compiler:
            compiler_path = Path(compiler).resolve()
            yield str(compiler_path.parent / name)
            if name == "binary-sign-tool" and len(compiler_path.parents) > 3:
                yield str(compiler_path.parents[3] / "toolchains" / "lib" / name)

    def _find_tool(self, name):
        for candidate in self._tool_candidates(name):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanException(f"required OHOS tool not found: {name}")

    def _sign_elf(self, binary):
        with VirtualBuildEnv(self).vars().apply():
            strip = self._find_tool("llvm-strip")
            objcopy = self._find_tool("llvm-objcopy")
            readelf = self._find_tool("llvm-readelf")
            signer = self._find_tool("binary-sign-tool")
            subprocess.run([strip, "--strip-debug", binary], check=True)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binary],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            signed = subprocess.run(
                [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
                capture_output=True,
                text=True,
            )
            sections = subprocess.run(
                [readelf, "-SW", binary], capture_output=True, text=True, check=True
            ).stdout
            dynamic = subprocess.run(
                [readelf, "-d", binary], capture_output=True, text=True, check=True
            ).stdout

        data = Path(binary).read_bytes()
        if signed.returncode != 0 or sections.count(".codesign") != 1:
            raise ConanException("failed to sign " + os.path.basename(binary))
        if "RPATH" in dynamic or "RUNPATH" in dynamic:
            raise ConanException(os.path.basename(binary) + " contains RPATH/RUNPATH")
        if b".conan2" in data or os.fsencode(self.build_folder) in data:
            raise ConanException(os.path.basename(binary) + " contains a build-host path")
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
