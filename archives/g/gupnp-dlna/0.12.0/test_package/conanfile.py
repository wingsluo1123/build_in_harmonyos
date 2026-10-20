#!/usr/bin/env python3
"""Conan test_package for gupnp-dlna 0.12.0 — Conan L1 official test.

Builds test_gupnp_dlna.c with CMake (CMakeDeps + CMakeToolchain) against the
packaged library and runs it on the OHOS device. The test is a real consumer
end-to-end check on the package's usable surface: it loads the DLNA profile
XML set through the public GUPnPDLNAProfileGuesser API, verifies profile
lookup (MP3/audio/mpeg) and relaxed/extended modes, checks the installed
layout, and parses the packaged GStreamer metadata backend module ELF to
check its .codesign section and exported entry point (the module is not
dlopen'ed: the static-glib GType split is a documented platform limitation).

The plugin-backed GstDiscoverer path is intentionally not executed: static
glib2/gstreamer mean every GStreamer plugin .so embeds its own glib/gst copy,
and the resulting cross-DSO GType registry split is a documented OHOS failure
mode (gst-plugins-bad1.0 1.28.5 notes). Device probe results for that path
are recorded in the version notes.

Runtime environment: the compile-time DATA_DIR is the configure-time prefix
("/"), so GUPNP_DLNA_PROFILE_DIR / GUPNP_DLNA_METADATA_BACKEND_DIR are
exported explicitly here (the recipe's package_info also does this for
downstream consumers).
"""
import glob
import os
import platform
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GupnpDlnaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv/VirtualBuildEnv must be kept: explicit generator lists
    # replace the defaults and env="conanrun" needs them (gupnp/gssdp 实撞).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps emits empty data for transitive deps unless they are
        # declared in the package's cpp_info.requires; declare the direct
        # dependencies of gupnp-dlna explicitly (gstreamer/gst-plugins-base
        # are static packages, glib2 supplies headers + static glib).
        self.requires("glib2/2.88.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CI 兼容: CMake try-compile 探测编译器 ABI 时拉起 lld，CI worker
        # 环境 lld 动态依赖的 libxml2.so.16 加载失败（E120 变体）。把编译器
        # 改写为 wrapper（内含 LD_LIBRARY_PATH=<SDK llvm/lib> 前置），
        # try-compile/编译/链接统一经 wrapper（gupnp-av 0.14.5 同款）。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or ""
        sdk = self._sdk_llvm_libdir()
        if cc and os.path.isfile(cc) and sdk and self._host_needs_clang_wrapper():
            bindir = os.path.join(self.generators_folder, "clang-wrappers")
            os.makedirs(bindir, exist_ok=True)
            for suffix in ("", "++"):
                w = os.path.join(bindir, "clang" + suffix)
                with open(w, "w", encoding="utf-8") as f:
                    f.write(
                        "#!/data/service/hnp/bin/bash\n"
                        f'export LD_LIBRARY_PATH="{sdk}:$LD_LIBRARY_PATH"\n'
                        f'exec "{cc}{suffix}" "$@"\n')
                os.chmod(w, 0o755)
            self.conf.update("tools.build:compiler_executables",
                             {"c": os.path.join(bindir, "clang"),
                              "cpp": os.path.join(bindir, "clang++"),
                              **{k: v for k, v in compilers.items()
                                 if k not in ("c", "cpp")}})
            self.output.info("test_package: clang wrapped for CMake try-compile")

    @staticmethod
    def _sdk_llvm_libdir():
        dirs = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        for d in reversed(dirs):
            if os.path.isdir(d):
                return d
        return None

    @staticmethod
    def _host_needs_clang_wrapper():
        """E120/E132 (lld -> libxml2.so.16) only reproduce on the x86_64 CI
        worker. On the aarch64 OHOS device the plain compiler works and OHOS
        refuses to exec unsigned script files (no binfmt_script), so the
        wrapper must not be used there."""
        return platform.machine().lower() not in ("aarch64", "arm64")

    def build(self):
        self._wrap_toolchain_compilers()
        cmake = CMake(self)
        # OHOS musl loader honours legacy DT_RPATH (not DT_RUNPATH); embed the
        # dependency lib dirs into the test binary (gupnp 1.6.10 precedent).
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p) and p not in rpaths:
                    rpaths.append(p)
        variables = {}
        if rpaths:
            flags = " ".join(
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths])
            variables["CMAKE_EXE_LINKER_FLAGS"] = flags
        cmake.configure(variables=variables)
        cmake.build()

    def _wrap_toolchain_compilers(self):
        sdk = self._sdk_llvm_libdir()
        if not sdk:
            return  # 非 OHOS 环境
        if not self._host_needs_clang_wrapper():
            return  # 真机原生 aarch64：直接 exec 脚本 wrapper 会被 OHOS 拒绝
        tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(tc_file):
            return
        with open(tc_file, encoding="utf-8") as f:
            content = f.read()
        if "clang-wrappers" in content:
            return
        # Same resolution order as generate(): the fallback wrapper must exec
        # the resolved compiler, not a hardcoded device path, or it diverges
        # from conan_toolchain.cmake and fails with a confusing "not found".
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        bindir = os.path.join(self.generators_folder, "clang-wrappers")
        os.makedirs(bindir, exist_ok=True)
        for suffix in ("", "++"):
            w = os.path.join(bindir, "clang" + suffix)
            with open(w, "w", encoding="utf-8") as f:
                f.write(
                    "#!/data/service/hnp/bin/bash\n"
                    f'export LD_LIBRARY_PATH="{sdk}:$LD_LIBRARY_PATH"\n'
                    f'exec "{cc}{suffix}" "$@"\n')
            os.chmod(w, 0o755)
        changed = False
        for var, wrapper in (("CMAKE_C_COMPILER", os.path.join(bindir, "clang")),
                             ("CMAKE_CXX_COMPILER", os.path.join(bindir, "clang++"))):
            new_content = re.sub(
                rf'(set\(\s*{var}\s+)"[^"]*"',
                rf'\1"{wrapper}"', content)
            if new_content != content:
                content = new_content
                changed = True
        if changed:
            with open(tc_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("test_package: conan_toolchain.cmake compilers -> wrappers")

    def test(self):
        package_dir = None
        libdirs = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            if dep.ref.name == "gupnp-dlna":
                package_dir = base
            for libdir in (dep.cpp_info.libdirs or []):
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p) and p not in libdirs:
                    libdirs.append(p)
        if package_dir:
            for sub in (os.path.join("lib", "gupnp-dlna"), "lib"):
                p = os.path.join(package_dir, sub)
                if os.path.isdir(p) and p not in libdirs:
                    libdirs.append(p)
        syslib = "/storage/Users/currentUser/usr/local/lib"
        if syslib not in libdirs:
            libdirs.append(syslib)
        ldpath = os.pathsep.join(libdirs)

        exports = [f'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"']
        if package_dir:
            profiles = os.path.join(package_dir, "share", "gupnp-dlna-2.0", "dlna-profiles")
            backend = os.path.join(package_dir, "lib", "gupnp-dlna")
            if os.path.isdir(profiles):
                exports.append(f'export GUPNP_DLNA_PROFILE_DIR="{profiles}"')
            if os.path.isdir(backend):
                exports.append(f'export GUPNP_DLNA_METADATA_BACKEND_DIR="{backend}"')

        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        exe = os.path.join(self.cpp.build.bindirs[0], "test_gupnp_dlna")
        script = "; ".join(exports + [f'"{exe}"'])
        self.run(f"{bash} -c '{script}'", env="conanrun")
