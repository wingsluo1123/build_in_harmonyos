import errno
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import tempfile
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class LibdispatchConan(ConanFile):
    name = "libdispatch"
    version = "6.4.1"
    description = "Grand Central Dispatch C/C++ runtime with bundled BlocksRuntime"
    license = "Apache-2.0"
    homepage = "https://github.com/swiftlang/swift-corelibs-libdispatch"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True, "musl-fts/*:shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if cross_building(self):
            raise ConanInvalidConfiguration("Full upstream validation requires a native build")

    def build_requirements(self):
        # Used only by the extended dispatch_io test, not by the delivered core.
        if self.settings.os in ("Linux", "OHOS"):
            self.test_requires("musl-fts/1.2.7")

    def layout(self):
        # Keep upstream PATCHES (a file) separate from exported patches/.
        # HMDFS workers can resolve those names case-insensitively.
        cmake_layout(self, src_folder="upstream")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["EXTENDED_TEST_SUITE"] = True
        tc.variables["ENABLE_SWIFT"] = False
        tc.variables["ENABLE_DTRACE"] = False
        # Upstream's CI mode; strict performance failures remain in the report.
        tc.variables["DISPATCH_LENIENT_TEST_DEADLINES"] = True
        if self.settings.os in ("Linux", "OHOS"):
            fts = self.dependencies["musl-fts"]
            tc.variables["FTS_INCLUDE_DIR"] = str(Path(fts.package_folder) / "include")
            tc.variables["FTS_LIBRARY"] = str(Path(self.build_folder) / "test-runtime/libfts.so.0")
        if self.settings.os == "OHOS":
            for language in ("C", "CXX"):
                for kind, value in (("SONAME", "-Wl,-soname,"),
                                    ("RUNTIME", "-Wl,-rpath,"),
                                    ("RPATH_LINK", "-Wl,-rpath-link,")):
                    tc.variables[f"CMAKE_SHARED_LIBRARY_{kind}_{language}_FLAG"] = value
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"] = ":"
        tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        run = VirtualRunEnv(self)
        run.generate()
        env = run.environment()
        env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        env.prepend_path("LD_LIBRARY_PATH", str(Path(self.build_folder) / "test-runtime"))
        if self.settings.os == "OHOS":
            # A worker's TMPDIR can itself be on HMDFS. Prove the required
            # DAC behaviour instead of trusting a directory's environment name.
            permission_tmp = self._permission_tmpdir()
            env.define("DISPATCH_TEST_PERMISSION_TMPDIR", permission_tmp)
        env.define("TMPDIR", str(Path(self.build_folder) / "test-tmp"))
        env.vars(self).save_script("libdispatch_tests")

    def _permission_tmpdir(self):
        candidates = [os.environ.get("TMPDIR", ""),
                      "/data/storage/el2/base/temp",
                      "/data/storage/el2/base/cache"]
        checked = set()
        for value in candidates:
            if not value or not Path(value).is_absolute():
                continue
            try:
                base = Path(value).resolve(strict=True)
            except OSError:
                continue
            if base in checked or not base.is_dir():
                continue
            checked.add(base)
            try:
                fixture = Path(tempfile.mkdtemp(prefix="libdispatch-dac-", dir=base))
            except OSError as error:
                self.output.info(f"Permission fixture candidate unavailable: {base}: {error}")
                continue
            child = fixture / "probe"
            denied = None
            try:
                fixture.chmod(0)
                try:
                    fd = os.open(child, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                except OSError as error:
                    denied = error.errno
                else:
                    os.close(fd)
                fixture.chmod(0o700)
                # A denial alone is insufficient: this task must also be able
                # to create in the same directory once permissions are restored.
                if denied == errno.EACCES:
                    fd = os.open(child, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                    os.close(fd)
                    self.output.info(f"PERMISSION_TMPDIR_DAC_PASS {base} EACCES={denied} restored=PASS")
                    return str(base)
                self.output.info(f"Permission fixture candidate rejected: {base}: errno={denied}")
            finally:
                # Only the unique mkdtemp directory and its exact probe belong
                # to us; never chmod or remove an existing parent directory.
                fixture.chmod(0o700)
                child.unlink(missing_ok=True)
                fixture.rmdir()
        raise ConanException("No OHOS temporary directory enforces EACCES and restored access")

    def _sign(self, path):
        if self.settings.os != "OHOS":
            return
        tool = shutil.which("binary-sign-tool")
        if not tool:
            raise ConanException("binary-sign-tool is required for native OHOS test execution")
        path = Path(path)
        output = path.with_name(path.name + ".signed")
        if output.exists():
            raise ConanException("Unexpected pre-existing signature output")
        self.run(f'"{tool}" sign -inFile "{path}" -outFile "{output}" -selfSign 1')
        if not output.is_file() or output.is_symlink():
            raise ConanException("Signer did not produce a regular ELF")
        output.chmod(stat.S_IMODE(path.stat().st_mode))
        output.replace(path)

    def build(self):
        apply_conandata_patches(self)
        root = Path(self.build_folder)
        (root / "test-tmp").mkdir(exist_ok=True)
        if self.settings.os in ("Linux", "OHOS"):
            fts_root = Path(self.dependencies["musl-fts"].package_folder).resolve()
            library = (fts_root / "lib/libfts.so.0").resolve(strict=True)
            if not library.is_relative_to(fts_root) or not library.is_file():
                raise ConanException("FTS input escaped the declared dependency package")
            private = root / "test-runtime"
            private.mkdir(exist_ok=True)
            shutil.copyfile(library, private / "libfts.so.0")
            self._sign(private / "libfts.so.0")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        for path in sorted(root.iterdir()):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open("rb") as stream:
                header = stream.read(20)
            if header[:4] == b"\x7fELF" and struct.unpack_from("<H", header, 16)[0] in (2, 3):
                self._sign(path)
        inventory = root / "upstream-inventory.json"
        junit = root / "upstream-junit.xml"
        self.run(f'ctest --show-only=json-v1 > "{inventory}"', cwd=self.build_folder,
                 env="libdispatch_tests")
        ids = [item["name"] for item in json.loads(inventory.read_bytes())["tests"]]
        if len(ids) != 37 or len(set(ids)) != 37:
            raise ConanException(f"Native full-suite registration drift: {len(ids)}")
        self.run(f'ctest --output-on-failure --no-tests=error --parallel 1 --output-junit "{junit}"',
                 cwd=self.build_folder, env="libdispatch_tests")
        cases = ET.parse(junit).getroot().findall("testcase")
        if sorted(item.get("name") for item in cases) != sorted(ids):
            raise ConanException("Upstream result IDs differ from registered test IDs")
        if any(item.find(tag) is not None for item in cases for tag in ("failure", "error", "skipped")):
            raise ConanException("Full upstream suite contains failed or skipped tests")
        self.output.info(f"UPSTREAM_N_OF_N_PASS {len(ids)}")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for path in (Path(self.package_folder) / "lib").glob("*.so"):
            self._sign(path)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdispatch")
        self.cpp_info.set_property("cmake_target_name", "libdispatch::libdispatch")
        self.cpp_info.libs = ["dispatch", "BlocksRuntime"]
        self.cpp_info.cflags = ["-fblocks"]
        self.cpp_info.cxxflags = ["-fblocks"]
        if not self.options.shared:
            self.cpp_info.defines = ["dispatch_STATIC", "BlocksRuntime_STATIC"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
