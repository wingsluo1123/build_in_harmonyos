#!/usr/bin/env python3
"""Conan recipe — vkbasalt 0.3.2.10 (Vulkan post-processing layer)

vkBasalt is a Vulkan post processing layer to enhance the visual graphics of
games (CAS / FXAA / SMAA / deband / DLS / LUT, plus ReShade FX shaders).
Build system: Meson (C/C++).

OHOS adaptation notes:
  - vkBasalt is a Vulkan implicit layer: it is loaded by the Vulkan loader at
    runtime and never links libvulkan (VK_NO_PROTOTYPES + dispatch table), so
    no "vulkan" pkg is required at build time. Headers (vulkan/vulkan.h +
    vulkan/vk_layer.h) come from the published vulkan-headers package.
  - Shaders (src/shader/meson.build) are compiled with glslangValidator at
    configure time -> tool_requires glslang (published).
  - keyboard_input uses X11 -> requires libx11 (published, x11.pc).
  - ELF signing: OHOS enforces code signing at load time; self-sign shipped
    .so with binary-sign-tool when present (never fails the build).
  - meson options: with_so/with_json default true; append_libdir_vkbasalt
    default false (keep libvkbasalt.so in lib/, json in share/vulkan/).
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class VkBasaltConan(ConanFile):
    name = "vkbasalt"
    version = "0.3.2.10"
    description = ("Vulkan post-processing layer (CAS/FXAA/SMAA/deband/DLS/LUT, "
                   "ReShade FX shaders)")
    license = "Zlib"
    homepage = "https://github.com/DadSchoorse/vkBasalt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # headers only (build-scripts): vulkan/vulkan.h + vulkan/vk_layer.h
        self.requires("vulkan-headers/vulkan-sdk-1.4.357.0",
                      transitive_headers=True)
        # reshade/spirv.hpp includes spirv/unified1/spirv.hpp
        self.requires("spirv-headers/vulkan-sdk-1.3.290.0",
                      transitive_headers=True)
        # keyboard_input_x11 needs X11/Xlib.h (libx11) and links libX11;
        # X11/X.h and other core protocol headers come from xorgproto.
        self.requires("libx11/1.8.13.1", transitive_headers=True,
                      transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")
        # glslangValidator for src/shader/meson.build (no glslc on OHOS)
        self.tool_requires("glslang/vulkan-sdk-1.3.290.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Force absolute binutils paths: MesonToolchain otherwise falls back
        # to bare 'llvm-ar' (absent from PATH on OHOS CI workers) -> meson
        # project() dies with "Unknown linker(s): [['llvm-ar']]".
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc_path = ce.get("c") or ""
        bindir = os.path.dirname(cc_path) if os.sep in cc_path else ""
        if bindir:
            for key, names in (("ar", ("llvm-ar", "ar")),
                               ("ranlib", ("llvm-ranlib", "ranlib"))):
                for name in names:
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        tc.binaries[key] = cand
                        break
        # Register glslangValidator explicitly (meson find_program checks
        # [binaries] first, then PATH).
        glslang_pkg = self.dependencies.build["glslang"].package_folder
        glslang_validator = os.path.join(glslang_pkg, "bin", "glslangValidator")
        if os.path.isfile(glslang_validator):
            tc.binaries["glslangValidator"] = glslang_validator

        # vkBasalt includes headers directly in several translation units.
        #   - vulkan/vk_layer.h / spirv/unified1/spirv.hpp: never via a meson
        #     dependency -> inject the header-only packages' include dirs.
        #   - keyboard_input_x11.cpp: meson builds that static_library WITHOUT
        #     x11_dep (the dependency is only attached to the shared library),
        #     so X11/Xlib.h + X11/X.h are not on the include path either;
        #     upstream finds them in the system prefix, OHOS needs them
        #     injected from libx11 + xorgproto.
        for dep_name in ("vulkan-headers", "spirv-headers", "libx11",
                         "xorgproto"):
            dep_pkg = self.dependencies[dep_name].package_folder
            dep_include = os.path.join(dep_pkg, "include")
            tc.c_args.append(f"-I{dep_include}")
            tc.cpp_args.append(f"-I{dep_include}")
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        # Make x11.pc (generated for libx11) visible to meson dependency('x11')
        self._append_dependency_pkg_config_paths()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        # 确保安装的共享库对加载器/消费者可读（OHOS 构建 worker 的 umask
        # 可能是 027，产物权限 750 会让非 owner 的测试进程无法 dlopen ->
        # "Error loading shared library"）。
        for lib_dir in (os.path.join(self.package_folder, "lib"),
                        os.path.join(self.package_folder, "bin")):
            if not os.path.isdir(lib_dir):
                continue
            for name in os.listdir(lib_dir):
                path = os.path.join(lib_dir, name)
                if os.path.isfile(path):
                    try:
                        os.chmod(path, 0o755)
                    except OSError:
                        pass
        self._self_sign_elfs()

    def _self_sign_elfs(self):
        # OHOS enforces ELF code signing at load time (dlopen/exec of an ELF
        # whose .codesign section is zero-filled -> EACCES "Permission denied"
        # on HarmonyOS PC). Sign locally with selfSign when the SDK tool is
        # present; keep the package runnable on device. Fully guarded: never
        # fails the build.
        if str(self.settings.os) != "OHOS":
            return
        # Probe for the signer on this host: CI workers keep it under
        # /data/service/hnp/bin, local dev machines under usr/local/bin.
        tool = None
        for candidate in ("/data/service/hnp/bin/binary-sign-tool",
                          "/storage/Users/currentUser/usr/local/bin/"
                          "binary-sign-tool"):
            if os.path.isfile(candidate):
                tool = candidate
                break
        if tool is None:
            import shutil as _shutil
            tool = _shutil.which("binary-sign-tool")
        if not tool:
            self.output.info("binary-sign-tool absent; skipping self-sign")
            return
        pkg = self.package_folder
        targets = (glob.glob(os.path.join(pkg, "lib", "**", "*.so"),
                             recursive=True) +
                   glob.glob(os.path.join(pkg, "lib", "**", "*.so.*"),
                             recursive=True) +
                   glob.glob(os.path.join(pkg, "bin", "*")))
        signed = 0
        for path in targets:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                out = path + ".signed"
                r = subprocess.run(
                    [tool, "sign", "-selfSign", "1", "-signAlg",
                     "SHA256withECDSA", "-inFile", path, "-outFile", out],
                    capture_output=True, timeout=60)
                if r.returncode == 0 and os.path.isfile(out):
                    shutil.copymode(path, out)
                    os.replace(out, path)
                    signed += 1
                elif os.path.isfile(out):
                    os.remove(out)  # don't ship a half-written artifact
            except Exception as e:  # noqa: BLE001 - best effort by design
                self.output.warn(f"self-sign skipped for {path}: {e}")
        self.output.info(f"self-signed {signed} ELF file(s) in package")

    def _append_dependency_pkg_config_paths(self):
        # meson dependency('x11') resolves via pkg-config; make sure the
        # generators folder (PkgConfigDeps output) plus dependency
        # pkgconfig dirs are on the pkg_config_path of the native file.
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join(
            "'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def package_info(self):
        self.cpp_info.libs = ["vkbasalt"]
        self.cpp_info.includedirs = []
        # implicit layer json lands under share/vulkan/implicit_layer.d
        self.cpp_info.set_property("pkg_config_name", "vkbasalt")
