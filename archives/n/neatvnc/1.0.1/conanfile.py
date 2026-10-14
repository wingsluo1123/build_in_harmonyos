"""NeatVNC 1.0.1 VNC server library for HarmonyOS PC."""

import hashlib
import os
import shutil
import stat
import subprocess
import uuid
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class NeatvncConan(ConanFile):
    name = "neatvnc"
    version = "1.0.1"
    package_type = "library"
    description = "A Neat VNC server library"
    homepage = "https://github.com/any1/neatvnc"
    license = "ISC"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("aml/1.0.0")
        self.requires("pixman/0.46.4.3")
        self.requires("zlib/1.3.2.1")
        # v1.0.1 always reads the libdrm fourcc header, even with H.264 off.
        self.requires("libdrm/2.4.133")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        # The 1.13.2 OHOS binary hard-codes a shell absent on this target.
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("NEATVNC_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = MesonToolchain(self)
        if str(self.settings.os) == "OHOS":
            compiler = self.conf.get("tools.build:compiler_executables",
                                     default={}, check_type=dict).get("c")
            if not compiler or not Path(compiler).is_absolute():
                raise ConanInvalidConfiguration("absolute OHOS compiler is required")
            # MesonToolchain reads AR from buildenv, not the compiler dict.
            # Bind the archiver to this compiler's SDK, including symlinked
            # HNP entrypoints, rather than relying on a worker's PATH.
            reported = subprocess.run([compiler, "-print-prog-name=llvm-ar"],
                                      check=True, capture_output=True, text=True,
                                      timeout=15).stdout.strip()
            candidates = [Path(compiler).parent / "llvm-ar",
                          Path(compiler).resolve().parent / "llvm-ar"]
            # A shell launcher is not a symlink: ask the actual Clang driver
            # for its adjacent SDK tool instead of guessing a versioned path.
            if Path(reported).is_absolute():
                candidates.append(Path(reported))
            archiver = next((path for path in candidates
                             if path.is_file() and os.access(path, os.X_OK)), None)
            if archiver is None:
                raise ConanInvalidConfiguration("compiler SDK llvm-ar is unavailable")
            tc.binaries["ar"] = str(archiver)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["tests"] = True
        tc.project_options["examples"] = False
        tc.project_options["benchmarks"] = False
        tc.project_options["jpeg"] = "disabled"
        tc.project_options["tls"] = "disabled"
        tc.project_options["nettle"] = "disabled"
        tc.project_options["gbm"] = "disabled"
        tc.project_options["h264"] = "disabled"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        # test/meson.build registers pixels and base64 with nettle disabled.
        self.run('meson test --print-errorlogs -j1 -C "{}"'.format(self.build_folder),
                 env=["conanbuild", "conanrun"])
        self.output.info("UPSTREAM_2_OF_2_PASS")

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS" and self.options.shared:
            libdir = Path(self.package_folder) / "lib"
            versioned = libdir / "libneatvnc.so.1.0.1"
            aliases = (libdir / "libneatvnc.so.1", libdir / "libneatvnc.so")
            if not versioned.is_file() or versioned.is_symlink():
                raise ConanInvalidConfiguration("versioned NeatVNC library is missing")
            if any(not alias.is_symlink() or not alias.samefile(versioned)
                   for alias in aliases):
                raise ConanInvalidConfiguration("NeatVNC library alias chain changed")
            compiler = self.conf.get("tools.build:compiler_executables",
                                     default={}, check_type=dict).get("c")
            if not compiler or not Path(compiler).is_absolute():
                raise ConanInvalidConfiguration("absolute OHOS compiler is required")
            tools = [Path(compiler).parent / name for name in
                     ("llvm-objcopy", "binary-sign-tool", "llvm-readelf")]
            if any(not tool.is_file() or not os.access(tool, os.X_OK)
                   for tool in tools):
                raise ConanInvalidConfiguration("OHOS ELF signing tools unavailable")
            self._resign_installed_elf(versioned, tools)
            expected = hashlib.sha256(versioned.read_bytes()).digest()
            for alias in aliases:
                alias.unlink()
                shutil.copy2(versioned, alias)
                if (alias.is_symlink() or not alias.is_file()
                        or hashlib.sha256(alias.read_bytes()).digest() != expected):
                    raise ConanInvalidConfiguration("NeatVNC library alias copy invalid")
                self._resign_installed_elf(alias, tools)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def _resign_installed_elf(self, library, tools):
        objcopy, signer, readelf = (str(tool) for tool in tools)
        nonce = uuid.uuid4().hex
        unsigned = library.with_name(f".{library.name}.{nonce}.unsigned")
        signed = library.with_name(f".{library.name}.{nonce}.signed")
        original_mode = stat.S_IMODE(library.stat().st_mode)
        try:
            subprocess.run([objcopy, "--remove-section", ".codesign",
                            str(library), str(unsigned)], check=True,
                           capture_output=True)
            subprocess.run([signer, "sign", "-inFile", str(unsigned),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True).stdout
            if sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration("re-signed ELF section count invalid")
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, library)
            self.output.info(f"RESIGNED_INSTALLED_ELF={library.name}")
        finally:
            for temporary in (unsigned, signed):
                if temporary.exists() and not temporary.is_symlink():
                    temporary.unlink()

    def package_info(self):
        self.cpp_info.libs = ["neatvnc"]
        self.cpp_info.set_property("cmake_file_name", "neatvnc")
        self.cpp_info.set_property("cmake_target_name", "neatvnc::neatvnc")
        self.cpp_info.set_property("pkg_config_name", "neatvnc")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
