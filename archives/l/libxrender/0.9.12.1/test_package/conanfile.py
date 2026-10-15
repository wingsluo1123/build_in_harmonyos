import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibxrenderTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c", "MANIFEST.yml"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.extra_exelinkflags.append("-Wl,--disable-new-dtags")
            toolchain.variables["CMAKE_BUILD_RPATH"] = ";".join(self._runtime_dirs(Path(self.dependencies["libxrender"].package_folder)))
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = self.conf.get("user.libxrender:signer", default=None) or shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        readelf = shutil.which("llvm-readelf")
        if not all(p and os.path.isfile(p) for p in [signer, objcopy, readelf]):
            raise ConanException("OHOS signer closure missing")
        subprocess.run([objcopy, "--remove-section", ".codesign", str(path)], check=True)
        temporary = str(path) + ".signed"
        subprocess.run([signer, "sign", "-inFile", str(path), "-outFile", temporary, "-selfSign", "1"], check=True)
        sections = subprocess.check_output([readelf, "-SW", temporary], text=True)
        if sections.count(".codesign") != 1:
            raise ConanException("Consumer signature section is not unique")
        os.chmod(temporary, 0o755)
        os.replace(temporary, path)

    def _pkgconfig_consumer(self, package_root, label):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None) or shutil.which("pkg-config")
        metadata_dirs = [str(package_root / "lib/pkgconfig"), self.generators_folder]
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "libxrender":
                continue
            for relative in ["share/pkgconfig", "lib/pkgconfig"]:
                directory = Path(dependency.package_folder, relative)
                if directory.is_dir():
                    metadata_dirs.append(str(directory))
        environment = dict(os.environ, PKG_CONFIG_PATH=os.pathsep.join(metadata_dirs))
        prefix = subprocess.check_output([pkg_config, "--variable=prefix", "xrender"], env=environment, text=True).strip()
        if Path(prefix).resolve() != package_root.resolve():
            raise ConanException("Installed xrender.pc is not relocatable")
        flags = shlex.split(subprocess.check_output([pkg_config, "--cflags", "--libs", "xrender"], env=environment, text=True))
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c") or shutil.which("cc")
        executable = Path(self.build_folder, label)
        args = [compiler, "-Wall", "-Wextra", "-Werror"]
        args += self.conf.get("tools.build:cflags", default=[])
        args += [str(Path(self.source_folder, "color_contract.c")), "-o", str(executable)] + flags
        args += self.conf.get("tools.build:exelinkflags", default=[])
        runtime = self._runtime_dirs(package_root)
        args += ["-Wl,--disable-new-dtags,-rpath," + ":".join(runtime), "-ldl"]
        subprocess.run(args, check=True, env=environment)
        self._sign(executable)
        environment["LD_LIBRARY_PATH"] = os.pathsep.join(runtime)
        if self.dependencies["libxrender"].options.shared:
            environment["XR_EXPECT_PROVIDER_PREFIX"] = str(package_root / "lib") + "/"
        subprocess.run([str(executable)], check=True, env=environment)
        return {"command": args, "runtime": runtime, "prefix": prefix, "rc": 0,
                "binary_bytes": executable.stat().st_size, "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()}

    def _runtime_dirs(self, package_root):
        runtime = [str(package_root / "lib")]
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "libxrender":
                continue
            runtime += [str(Path(dependency.package_folder, d)) if not os.path.isabs(d) else d
                        for d in dependency.cpp_info.libdirs]
        return list(dict.fromkeys(runtime))

    def test(self):
        if not can_run(self):
            raise ConanException("libxrender target consumers are not runnable")
        results = []
        for name in ["libxrender_api_surface", "libxrender_color_contract"]:
            executable = Path(self.cpp.build.bindir, name).resolve()
            self._sign(executable)
            self.run(shlex.quote(str(executable)), env="conanrun")
            results.append({"id": name, "rc": 0, "binary_bytes": executable.stat().st_size,
                            "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()})
        dependency = self.dependencies["libxrender"]
        package = Path(dependency.package_folder)
        results.append({"id": "installed-pkgconfig", **self._pkgconfig_consumer(package, "pkgconfig-consumer")})
        evidence = Path(self.build_folder, "libxrender-consumer-evidence")
        evidence.mkdir(exist_ok=True)
        (evidence / "consumer.json").write_text(json.dumps({"total": 3, "passed": 3, "failed": 0, "results": results, "shared": bool(dependency.options.shared),
            "provider_binaries": {str(p.relative_to(package)): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                  for p in (package / "lib").glob("libXrender.*") if p.is_file()}}), encoding="utf-8")
        self.output.info("CONSUMER_TEST_PASS=3/3")
        if str(self.settings.os) == "OHOS":
            if platform.system() != "HarmonyOS" or platform.machine() != "aarch64":
                raise ConanException("Harmony-specific relocated ELF test requires native target")
            relocated = Path(self.build_folder, "harmony-relocated")
            shutil.copytree(package, relocated)
            if dependency.options.shared:
                readelf = shutil.which("llvm-readelf")
                library = relocated / "lib/libXrender.so.1.3.0"
                sections = subprocess.check_output([readelf, "-SW", str(library)], text=True)
                if sections.count(".codesign") != 1:
                    raise ConanException("Relocated HarmonyOS provider signature is not unique")
                dynamic = subprocess.check_output([readelf, "-d", str(library)], text=True)
                if "(RPATH)" in dynamic or "(RUNPATH)" in dynamic:
                    raise ConanException("Installed provider retains producer runtime paths")
                if (relocated / "lib/libXrender.so.1").read_bytes() != library.read_bytes():
                    raise ConanException("HarmonyOS SONAME alias byte identity mismatch")
            harmony = self._pkgconfig_consumer(relocated, "harmony-relocated-consumer")
            (evidence / "harmony.json").write_text(json.dumps({"total": 1, "passed": 1, "failed": 0,
                "id": "harmony-relocated-signed-provider", "uname": list(os.uname()), "result": harmony}), encoding="utf-8")
            self.output.info("HARMONY_TEST_COUNT=1; HARMONY_TEST_PASS=1/1; CLEAN_EXIT=0")
