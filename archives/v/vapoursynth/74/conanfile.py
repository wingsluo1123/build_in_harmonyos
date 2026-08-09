#!/usr/bin/env python3
"""Conan recipe for VapourSynth 74."""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class VapoursynthConan(ConanFile):
    name = "vapoursynth"
    version = "74"
    description = "A video processing framework with simplicity in mind"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.vapoursynth.com/"
    url = "https://github.com/vapoursynth/vapoursynth"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "vsscript": [True, False],
        "python_module": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "vsscript": False,
        "python_module": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zimg/3.0.6")

    def generate(self):
        if self.options.python_module:
            self._ensure_python_build_tools()

        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["enable_core"] = True
        tc.project_options["enable_guard_pattern"] = False
        tc.project_options["enable_x86_asm"] = False
        tc.project_options["enable_vsscript"] = bool(self.options.vsscript)
        tc.project_options["enable_vspipe"] = False
        tc.project_options["enable_python_module"] = bool(self.options.python_module)
        tc.project_options["build_wheel"] = False
        self._select_ohos_meson_linker(tc)
        tc.generate()
        if self.options.python_module:
            self._inject_meson_cython()
        self._inject_meson_archiver()
        self._inject_meson_pkg_config()
        self._wrap_nonexecutable_meson_compilers()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING.LESSER", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        Meson(self).install()
        self._ensure_unversioned_shared_libraries()
        self._package_python_module()
        self._package_upstream_tests()
        self._sign_shared_libraries()
        self._ensure_shared_library_permissions()

    def package_info(self):
        self.cpp_info.libs = ["vapoursynth"]
        if self.options.vsscript:
            self.cpp_info.libs.append("vsscript")
        self.cpp_info.includedirs = ["include/vapoursynth", "include"]
        self.cpp_info.set_property("cmake_file_name", "vapoursynth")
        self.cpp_info.set_property("cmake_target_name", "vapoursynth::vapoursynth")
        self.cpp_info.set_property("pkg_config_name", "vapoursynth")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

        libdir = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        pythondir = os.path.join(self.package_folder, "python")
        if os.path.isdir(pythondir):
            self.runenv_info.prepend_path("PYTHONPATH", pythondir)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(pythondir, "vapoursynth"))

    def _ensure_python_build_tools(self):
        has_cython = False
        try:
            subprocess.run(
                [
                    "python3",
                    "-c",
                    (
                        "import Cython; "
                        "version = tuple(int(part) for part in Cython.__version__.split('.')[:2]); "
                        "raise SystemExit(0 if version >= (3, 1) else 1)"
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            has_cython = True
        except (OSError, subprocess.CalledProcessError):
            pass
        if not has_cython:
            self.run("python3 -m pip install --user Cython==3.1.2")
        self._prepend_cython_wrapper()

    def _prepend_cython_wrapper(self):
        wrapper_dir = os.path.join(self.generators_folder, "cython-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        shell = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "/bin/sh"
        for name in ("cython", "cython3"):
            wrapper = os.path.join(wrapper_dir, name)
            with open(wrapper, "w", encoding="utf-8") as handle:
                handle.write("#!{}\nexec python3 -m cython \"$@\"\n".format(shell))
            os.chmod(wrapper, 0o755)
        os.environ["PATH"] = wrapper_dir + os.pathsep + os.environ.get("PATH", "")

    def _inject_meson_cython(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        cython = os.path.join(self.generators_folder, "cython-wrapper", "cython")
        if not os.path.isfile(native_file) or not os.path.isfile(cython):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content or "\ncython =" in content:
            return
        shell = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "/bin/sh"
        insertion = "[binaries]\ncython = ['{}', '{}']\n".format(
            shell.replace("\\", "/"),
            cython.replace("\\", "/"),
        )
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))

    def _inject_meson_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))

    def _inject_meson_pkg_config(self):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        if "\npkg-config =" not in content and "\npkgconfig =" not in content:
            insertion = "[binaries]\npkg-config = '{}'\n".format(str(pkg_config).replace("\\", "/"))
            content = content.replace("[binaries]\n", insertion, 1)
        if "pkg_config_path =" not in content and "[built-in options]" in content:
            pc_path = self.generators_folder.replace("\\", "/")
            content = content.replace(
                "[built-in options]\n",
                "[built-in options]\npkg_config_path = ['{}']\n".format(pc_path),
                1,
            )
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _wrap_nonexecutable_meson_compilers(self):
        if self.settings.os != "OHOS":
            return
        shell = "/system/bin/sh"
        if not os.path.exists(shell):
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            lines = handle.readlines()

        changed = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            for key in ("c", "cpp"):
                prefix = "{} = '".format(key)
                if not stripped.startswith(prefix) or not stripped.endswith("'"):
                    continue
                compiler = stripped[len(prefix):-1]
                if os.path.exists(compiler) and not self._can_execute(compiler):
                    lines[idx] = "{} = ['{}', '{}']\n".format(key, shell, compiler)
                    changed = True

        if changed:
            with open(native_file, "w", encoding="utf-8") as handle:
                handle.writelines(lines)

    def _select_ohos_meson_linker(self, toolchain):
        if self.settings.os != "OHOS":
            return
        linker = self._find_ohos_linker()
        if not linker:
            return
        # Meson probes the linker before normal link_args are applied.
        toolchain.c_ld = linker.replace("\\", "/")
        toolchain.cpp_ld = linker.replace("\\", "/")

    @staticmethod
    def _can_execute(path):
        try:
            subprocess.run(
                [path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except OSError:
            return False

    def _ensure_unversioned_shared_libraries(self):
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        unversioned = os.path.join(libdir, "libvapoursynth.so")
        versioned = os.path.join(libdir, "libvapoursynth.so.4")
        if not os.path.exists(versioned):
            matches = glob.glob(os.path.join(self.package_folder, "**", "libvapoursynth.so.4"), recursive=True)
            for match in matches:
                if os.path.normpath(match) != os.path.normpath(versioned):
                    shutil.copy2(match, versioned)
                    break
        if os.path.exists(versioned) and not os.path.exists(unversioned):
            shutil.copy2(versioned, unversioned)

    def _package_python_module(self):
        if not self.options.python_module:
            return
        pythondir = os.path.join(self.package_folder, "python", "vapoursynth")
        os.makedirs(pythondir, exist_ok=True)
        for source_root, _, files in os.walk(self.package_folder):
            if os.path.normpath(source_root).startswith(os.path.normpath(pythondir)):
                continue
            if os.path.basename(source_root) != "vapoursynth":
                continue
            for filename in files:
                if filename.endswith((".py", ".pyi", ".so")) or filename.startswith("libvapoursynth.so"):
                    shutil.copy2(os.path.join(source_root, filename), os.path.join(pythondir, filename))
        if not glob.glob(os.path.join(pythondir, "vapoursynth*.so")):
            raise RuntimeError("Python module was requested but vapoursynth extension was not packaged")
        versioned = os.path.join(pythondir, "libvapoursynth.so.4")
        unversioned = os.path.join(pythondir, "libvapoursynth.so")
        if os.path.exists(versioned) and not os.path.exists(unversioned):
            shutil.copy2(versioned, unversioned)

    def _package_upstream_tests(self):
        tests_dir = os.path.join(self.package_folder, "tests", "upstream")
        copy(self, "*", src=os.path.join(self.source_folder, "test"), dst=tests_dir)
        expr_src = os.path.join(self.source_folder, "src", "core", "expr")
        expr_dst = os.path.join(self.package_folder, "tests", "exprdebugger", "src", "core", "expr")
        copy(self, "expr.cpp", src=expr_src, dst=expr_dst)
        copy(self, "expr.h", src=expr_src, dst=expr_dst)
        copy(self, "main.cpp", src=expr_src, dst=expr_dst)

    def _sign_shared_libraries(self):
        if self.settings.os != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not os.path.exists(objcopy) or not os.path.exists(signer):
            return
        for shared_lib in glob.glob(os.path.join(self.package_folder, "**", "*.so*"), recursive=True):
            if os.path.islink(shared_lib):
                continue
            signed = shared_lib + ".signed"
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, shared_lib), quiet=True)
            self.run(
                '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, shared_lib, signed),
                quiet=True,
            )
            os.replace(signed, shared_lib)

    def _ensure_shared_library_permissions(self):
        if self.settings.os != "OHOS":
            return
        for shared_lib in glob.glob(os.path.join(self.package_folder, "**", "*.so*"), recursive=True):
            if not os.path.islink(shared_lib):
                os.chmod(shared_lib, 0o755)

    def _find_ohos_tool(self, name):
        found = shutil.which(name)
        if found:
            return found
        for prefix in ("/storage/Users/currentUser/usr/local/bin", "/data/service/hnp/bin"):
            candidate = os.path.join(prefix, name)
            if os.path.exists(candidate):
                return candidate
        return name

    @staticmethod
    def _find_ohos_linker():
        for candidate in ("/data/service/hnp/bin/ld", "/data/service/hnp/bin/ld.bfd"):
            if os.path.exists(candidate):
                return candidate
        return ""
