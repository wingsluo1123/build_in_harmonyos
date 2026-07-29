#!/usr/bin/env python3
"""Conan recipe for slang 2026.14 — CMake-based shader compiler.

Slang is a shading language compiler supporting HLSL/Slang→SPIR-V/GLSL/HLSL.
Built as a static library (R26) with command-line tools (slangc, slangi).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    collect_libs,
)


class SlangConan(ConanFile):
    name = "slang"
    version = "2026.14"
    description = "Slang is a shading language compiler supporting HLSL/Slang to SPIR-V/GLSL/HLSL targets"
    license = "MIT"
    homepage = "https://github.com/shader-slang/slang"
    url = ""  # CI fills this

    package_type = "library"

    # R32: settings.os must use in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download the main tarball
        get(self, **self.conan_data["sources"], strip_root=True)
        # The GitHub tarball does not include git submodules.
        # Download required submodules.
        self._download_submodules()

    def _find_git(self):
        """Find git executable in common HarmonyOS paths."""
        for path in ["/data/service/hnp/bin/git", "/usr/bin/git", "/usr/local/bin/git"]:
            if os.path.exists(path):
                return path
        return shutil.which("git")

    def _download_submodules(self):
        """Download git submodules required for building slang.

        The GitHub release tarball does not include submodule contents.
        We download each required submodule as a tarball from GitHub's
        archive API, which works without git and without SSL issues.
        """
        submodules = [
            ("external/unordered_dense", "martinus/unordered_dense",
             "73f3cbb237e84d483afafc743f1f14ec53e12314"),
            ("external/miniz", "richgel999/miniz",
             "6ef6c68f4fcbb8287aa8edf9c6670804932f41c6"),
            ("external/lz4", "lz4/lz4",
             "7f71be01f2c6f6b2c3cddb67eef8c38eab12ffd4"),
            ("external/cmark", "swiftlang/swift-cmark",
             "924936d0427cb25a61169739a7660230bffa6ea6"),
            ("external/vulkan", "KhronosGroup/Vulkan-Headers",
             "387259ecf4b0fe0cfac161b1d0b0a74e42796710"),
            ("external/spirv-headers", "KhronosGroup/SPIRV-Headers",
             "29981f65241605e08b0ede4cfeb999fe3b723c6a"),
            ("external/spirv-tools", "KhronosGroup/SPIRV-Tools",
             "0d6fd73ca73830ccab5fa1f00ed5ed40124e2c55"),
            ("external/glslang", "KhronosGroup/glslang",
             "d1f52c8993a501bd52d4fbd044bfeb9ecdceb9f4"),
            ("external/fast_float", "fastfloat/fast_float",
             "e0b53eaf63c6d00e0725788ef1dbb759aa321d79"),
            ("external/lua", "lua/lua",
             "3fe7be956f23385aa1950dc31e2f25127ccfc0ea"),
        ]

        src_folder = self.source_folder
        git_bin = self._find_git()

        for path, repo, commit in submodules:
            full_path = os.path.join(src_folder, path)
            # Check if already populated
            if os.listdir(full_path) if os.path.exists(full_path) else []:
                has_content = any(
                    os.path.exists(os.path.join(full_path, f))
                    for f in ["CMakeLists.txt", "meson.build", "onelua.c", "include"]
                )
                if has_content:
                    continue  # Already populated

            self.output.info(f"Downloading submodule: {path}")
            os.makedirs(full_path, exist_ok=True)

            # Try git clone first, then fallback to tarball download
            cloned = False
            if git_bin:
                repo_url = f"https://ghfast.top/https://github.com/{repo}.git"
                try:
                    subprocess.run(
                        [git_bin, "clone", "--depth", "1", repo_url, full_path],
                        check=True, capture_output=True, timeout=300
                    )
                    subprocess.run(
                        [git_bin, "fetch", "--depth", "1", repo_url, commit],
                        cwd=full_path, check=True, capture_output=True, timeout=300
                    )
                    subprocess.run(
                        [git_bin, "checkout", commit],
                        cwd=full_path, check=True, capture_output=True, timeout=30
                    )
                    cloned = True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    pass

            if not cloned:
                # Fallback: download as tarball from GitHub archive API
                self._download_submodule_tarball(path, repo, commit)

    def _download_submodule_tarball(self, path, repo, commit):
        """Fallback: download submodule as tarball.

        Uses Conan's built-in get() which handles SSL verification properly.
        Falls back to urllib with SSL verification enabled (not disabled).
        """
        archive_url = f"https://ghfast.top/https://github.com/{repo}/archive/{commit}.tar.gz"

        src_folder = self.source_folder
        full_path = os.path.join(src_folder, path)
        os.makedirs(full_path, exist_ok=True)

        # Preferred: use Conan's built-in download (handles SSL verification internally)
        try:
            get(self, archive_url, destination=full_path, strip_root=True)
            return
        except Exception as e:
            self.output.warning(f"Conan get() failed for {path}: {e}, trying urllib fallback")

        # Fallback: urllib with SSL verification enabled
        import ssl
        import urllib.request
        import tarfile
        import io

        ctx = ssl.create_default_context()
        req = urllib.request.Request(archive_url, headers={"User-Agent": "conan/2"})
        with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
            data = resp.read()

        # Extract tarball with path traversal protection
        extract_dir = full_path + "_extract"
        os.makedirs(extract_dir, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            safe_members = [
                m for m in tar.getmembers()
                if not (m.name.startswith("/") or ".." in m.name)
            ]
            tar.extractall(extract_dir, members=safe_members)

        # Move contents from the top-level directory to the target path
        extracted = os.listdir(extract_dir)
        if extracted:
            src_dir = os.path.join(extract_dir, extracted[0])
            for item in os.listdir(src_dir):
                src_item = os.path.join(src_dir, item)
                dst_item = os.path.join(full_path, item)
                if os.path.exists(dst_item):
                    if os.path.isdir(dst_item):
                        shutil.rmtree(dst_item)
                    else:
                        os.remove(dst_item)
                shutil.move(src_item, dst_item)
        shutil.rmtree(extract_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-same-name library must be static
        tc.variables["SLANG_LIB_TYPE"] = "STATIC"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Disable platform-specific features not available on OHOS
        tc.variables["SLANG_ENABLE_CUDA"] = "OFF"
        tc.variables["SLANG_ENABLE_OPTIX"] = "OFF"
        tc.variables["SLANG_ENABLE_DXIL"] = "OFF"
        tc.variables["SLANG_ENABLE_TESTS"] = "OFF"
        tc.variables["SLANG_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["SLANG_ENABLE_SLANG_RHI"] = "OFF"
        tc.variables["SLANG_ENABLE_GFX"] = "OFF"
        tc.variables["SLANG_SLANG_LLVM_FLAVOR"] = "DISABLE"
        tc.variables["SLANG_EXCLUDE_DAWN"] = "ON"
        tc.variables["SLANG_EXCLUDE_TINT"] = "ON"
        tc.variables["SLANG_ENABLE_SLANGD"] = "OFF"
        tc.variables["SLANG_ENABLE_REPLAYER"] = "OFF"
        tc.variables["SLANG_ENABLE_PCH"] = "OFF"
        tc.variables["SLANG_STANDARD_MODULE_DEVELOP_BUILD"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()

        # On HarmonyOS, newly built binaries need ELF signing before execution.
        # The build process generates and executes build-time tools (generators),
        # so we need to sign binaries during the build, not just after.
        if self.settings.os in ("Linux", "OHOS"):
            self._build_with_signing(cmake)
        else:
            cmake.build()

        # Sign all final binaries
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _build_with_signing(self, cmake):
        """Run cmake build with automatic binary signing on HarmonyOS.

        The build process generates executables that are then executed
        during the same build. On HarmonyOS, these must be signed first.
        This method catches 'Operation not permitted' errors, signs
        the affected binary, and retries the build.
        """
        max_retries = 50  # Safety limit
        build_dir = self.build_folder

        # Pre-check signing tools to avoid infinite retry loop
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            raise ConanException(
                f"Signing tools missing on OHOS: "
                f"binary-sign-tool={'found' if sign_tool else 'MISSING'}, "
                f"llvm-objcopy={'found' if objcopy else 'MISSING'}. "
                f"Build requires these tools for ELF binary signing."
            )

        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["cmake", "--build", ".", "--", "-j1"],
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 60 minutes per make invocation
                )
            except subprocess.TimeoutExpired:
                self.output.info(f"Build timed out on attempt {attempt+1}, retrying...")
                continue  # Retry - build will resume from where it left off

            if result.returncode == 0:
                self.output.info("Build completed successfully")
                return

            # Check for "Operation not permitted" (unsigned binary)
            combined_output = result.stderr + result.stdout
            if "Operation not permitted" in combined_output:
                import re
                unsigned_bins = set()
                for line in combined_output.split('\n'):
                    if 'Operation not permitted' not in line:
                        continue
                    # Error format: "/bin/sh: ../path/to/binary: Operation not permitted"
                    # Match both absolute (/path/...) and relative (../path/...) paths
                    matches = re.findall(r'((?:/|\.\./)[^\s:]+)', line)
                    for match in matches:
                        # Skip shell paths
                        if match in ('/bin/sh', '/bin/bash', '/data/service/hnp/bin/bash'):
                            continue
                        basename = os.path.basename(match)
                        # Resolve relative paths against build dir
                        if not os.path.isabs(match):
                            resolved = os.path.normpath(os.path.join(build_dir, match))
                        else:
                            resolved = match
                        if os.path.exists(resolved) and os.access(resolved, os.X_OK):
                            unsigned_bins.add(resolved)
                        elif basename and basename not in ('sh', 'bash'):
                            # Fallback: search by basename in build tree using os.walk
                            # (relative paths may be from subdirectories like prelude/)
                            for root, dirs, files in os.walk(build_dir):
                                if basename in files:
                                    found_path = os.path.join(root, basename)
                                    if os.path.exists(found_path):
                                        unsigned_bins.add(found_path)
                                        break

                if unsigned_bins:
                    for bin_path in unsigned_bins:
                        self._sign_single_binary(bin_path)
                    continue  # Retry the build

            # Different error - report it
            self.output.error(f"Build failed (attempt {attempt+1}):")
            self.output.error(result.stderr[-2000:] if result.stderr else result.stdout[-2000:])
            raise ConanException(f"Build failed: {result.returncode}")

        raise ConanException(f"Build failed after {max_retries} retries (binary signing loop)")

    def _sign_single_binary(self, bin_path):
        """Sign a single ELF binary on HarmonyOS."""
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            return
        try:
            subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                          capture_output=True, timeout=10, check=True)
            subprocess.run([sign_tool, "sign", "-inFile", bin_path,
                           "-outFile", bin_path, "-selfSign", "1"],
                          capture_output=True, timeout=10, check=True)
            os.chmod(bin_path, 0o755)
            self.output.info(f"Signed: {os.path.basename(bin_path)}")
        except subprocess.CalledProcessError as e:
            self.output.warning(f"Signing tool failed for {bin_path}: {e.stderr.decode() if e.stderr else e}")
        except Exception as e:
            self.output.warning(f"Failed to sign {bin_path}: {e}")

    def _sign_binaries(self):
        """Sign ELF binaries on HarmonyOS to allow execution."""
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            return  # Not on HarmonyOS or tools not found

        build_dir = self.build_folder
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                if f.endswith(".dwarf"):
                    continue
                fpath = os.path.join(root, f)
                if os.access(fpath, os.X_OK):
                    try:
                        subprocess.run([objcopy, "--remove-section", ".codesign", fpath],
                                      capture_output=True, timeout=10, check=True)
                        subprocess.run([sign_tool, "sign", "-inFile", fpath,
                                       "-outFile", fpath, "-selfSign", "1"],
                                      capture_output=True, timeout=10, check=True)
                        os.chmod(fpath, 0o755)
                    except subprocess.CalledProcessError as e:
                        self.output.warning(f"Signing tool failed for {fpath}: {e.stderr.decode() if e.stderr else e}")
                    except Exception as e:
                        self.output.warning(f"Failed to sign {fpath}: {e}")

    def _find_tool(self, name):
        """Find a tool in common paths."""
        for path in ["/data/service/hnp/bin", "/usr/bin", "/usr/local/bin"]:
            full = os.path.join(path, name)
            if os.path.exists(full):
                return full
        return shutil.which(name)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy additional static libraries needed for linking
        # (libslang-compiler.a references symbols from these)
        pkg_lib = os.path.join(self.package_folder, "lib")
        # CMake may place libraries under a build_type subdirectory
        build_type = str(self.settings.build_type) if self.settings.build_type else "Release"
        candidate_dirs = [
            os.path.join(self.build_folder, build_type, "lib"),
            os.path.join(self.build_folder, "lib"),
        ]
        for lib in ["libcore.a", "libcompiler-core.a", "libslang-cpp-parser.a"]:
            found = False
            for build_lib in candidate_dirs:
                src = os.path.join(build_lib, lib)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(pkg_lib, lib))
                    found = True
                    break
            if not found:
                self.output.warning(f"Required library {lib} not found in candidate dirs; "
                                    f"downstream linking may fail")

    def package_info(self):
        self.cpp_info.libs = ["slang-compiler", "slang-cpp-parser", "compiler-core", "core", "slang-rt"]
        self.cpp_info.bindirs = ["bin"]
        # Slang modules loaded at runtime
        self.cpp_info.libdirs = ["lib", "lib/slang-standard-module-2026.14"]
