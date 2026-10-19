#!/usr/bin/env python3
"""Conan recipe — libdisplay-info 0.4.0 (meson).

EDID (Extended Display Identification Data) and DisplayID parsing library:
the display-metadata dependency of wlroots' DRM backend and of other
compositor/display tooling. Pure C, no platform subsystem: the only
non-libc requirement is `libm`, and the only build-time data file is
hwdata's `pnp.ids` (EDID manufacturer ID -> name table).

OHOS packaging notes
--------------------
* hwdata: upstream does
  `dependency('hwdata', required: false, native: true)` and, when found,
  reads `pkgdatadir` from it to locate `pnp.ids`. OHOS has no system
  hwdata, so the packaged `hwdata/0.411` conan package provides the data.
  Conan's own pkg-config stub has no `pkgdatadir` variable (conan only
  synthesises libdir/includedir-style ones), so `generate()` writes the
  `hwdata.pc` meson looks up (MesonToolchain points meson's
  `pkg_config_path` at the generators folder) with `pkgdatadir` pointing at
  the packaged `share/hwdata`. Upstream's own lookup path stays intact:
  no fallback patch, no network access at build time, and the ID table
  stays a versioned conan dependency instead of a file copied around.
* 0001-memory-stream-portable.patch: the C library on this platform
  implements memory streams incorrectly - `fclose()` on an
  `open_memstream()` stream fails with EBADF and discards the buffer, so
  the strings upstream collects that way come back NULL and the process
  aborts with SIGTRAP while exiting. The patch replaces those two call
  sites (`info.c`/`memory-stream.c` in the library and `join_str()` in the
  CLI) with plain growable buffers.
* meson in the OHOS sandbox cannot probe bare compiler names (`clang`,
  `llvm-ar`, ...): the sandbox refuses to exec bare names resolved through
  PATH, so `[binaries]` gets absolute paths for c/cpp/ar/ranlib/strip.
* This package ships the library only (lib + headers + .pc). The
  `di-edid-decode` CLI built by the same meson project belongs to the
  separate `libdisplay-info-tools` package, which owns `bin/` alone.
* HarmonyOS only loads ELF objects carrying a valid `.codesign` section,
  so the installed `.so` is signed in `package()`.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.meson import Meson, MesonToolchain


class LibdisplayInfoConan(ConanFile):
    name = "libdisplay-info"
    version = "0.4.0"
    description = "EDID and DisplayID library for parsing display metadata"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/libdisplay-info"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdisplay-info supports Linux and OHOS, not {self.settings.os}"
            )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        # Build-time data dependency (pnp.ids, the EDID manufacturer table).
        # The data is compiled into the library, so nothing is needed at
        # runtime.  See the module docstring for how meson finds it.
        self.requires("hwdata/0.411")

    def layout(self):
        # meson refuses to configure when source and build directories are
        # the same, so keep the upstream tree at the root and build in build/.
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # Upstream builds di-edid-decode and the test programs
        # unconditionally; v4l-utils (only used to regenerate the test
        # fixtures) must stay offline.
        tc.project_options["wrap_mode"] = "nodownload"
        # dependency('hwdata', native: true) is a build-machine lookup; keep
        # the generators folder (where hwdata.pc is written) on that path too
        # so the lookup also works for a genuine cross build.
        tc.build_pkg_config_path = self.generators_folder.replace("\\", "/")
        tc.generate()
        self._write_hwdata_pc()
        self._inject_meson_archiver()

    def _write_hwdata_pc(self):
        """Write the hwdata.pc meson resolves dependency('hwdata') through."""
        pkgdatadir = os.path.join(
            self.dependencies["hwdata"].package_folder, "share", "hwdata"
        ).replace("\\", "/")
        pnp_ids = os.path.join(pkgdatadir, "pnp.ids")
        if not os.path.isfile(pnp_ids):
            raise ConanException(
                f"hwdata/0.411 does not provide share/hwdata/pnp.ids: {pnp_ids} missing"
            )
        content = (
            f"prefix={pkgdatadir}\n"
            "datadir=${prefix}\n"
            "pkgdatadir=${prefix}\n"
            "\n"
            "Name: hwdata\n"
            "Description: Hardware identification and configuration data\n"
            "Version: 0.411\n"
        )
        with open(os.path.join(self.generators_folder, "hwdata.pc"), "w",
                  encoding="utf-8") as fh:
            fh.write(content)

    def _inject_meson_archiver(self):
        # MesonToolchain only writes c/cpp into [binaries]; meson then probes
        # the archiver by bare name, which the OHOS sandbox cannot exec
        # ("Unknown linker(s): llvm-ar"), so append absolute paths.
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar, ranlib = ce.get("ar"), ce.get("ranlib")
        bindir = ""
        cc = ce.get("c") or ""
        if os.path.sep in cc:
            bindir = os.path.dirname(cc)
        if not ar and bindir:
            candidate = os.path.join(bindir, "llvm-ar")
            if os.path.isfile(candidate):
                ar = candidate
        if not ranlib and bindir:
            candidate = os.path.join(bindir, "llvm-ranlib")
            if os.path.isfile(candidate):
                ranlib = candidate
        if not ar:
            ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ranlib:
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        strip = shutil.which("llvm-strip") or shutil.which("strip")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (ar and os.path.isfile(native_file)):
            return
        with open(native_file, encoding="utf-8") as fh:
            content = fh.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        extra = "ar = '%s'\n" % ar
        if ranlib:
            extra += "ranlib = '%s'\n" % ranlib
        if strip:
            extra += "strip = '%s'\n" % strip
        with open(native_file, "w", encoding="utf-8") as fh:
            fh.write(content.replace("[binaries]\n", "[binaries]\n" + extra, 1))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # The CLI built by the same meson project belongs to the
        # libdisplay-info-tools package - drop it here so no file ever has
        # two owners.
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            rmdir(self, bindir)
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """Sign every installed .so: HarmonyOS only loads signed ELF objects."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for name in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, name)
            if os.path.isfile(path) and not os.path.islink(path) and ".so" in name:
                self._sign_ohos_elf(path)

    def _sign_ohos_elf(self, path):
        tools = {}
        for name in ("llvm-readelf", "llvm-objcopy", "binary-sign-tool"):
            tools[name] = shutil.which(name) or os.path.join(
                "/data/service/hnp/bin", name
            )
            if not os.path.isfile(tools[name]):
                raise ConanException(f"required OHOS tool is missing: {name}")
        temporary = path + ".signed"
        self.run(
            f'"{tools["llvm-objcopy"]}" --remove-section .codesign "{path}" '
            f'2>/dev/null || true'
        )
        subprocess.run(
            [
                tools["binary-sign-tool"], "sign",
                "-inFile", path, "-outFile", temporary, "-selfSign", "1",
            ],
            check=True,
            timeout=120,
        )
        sections = subprocess.run(
            [tools["llvm-readelf"], "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed ELF has invalid .codesign count: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def package_info(self):
        self.cpp_info.libs = ["display-info"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "libdisplay-info")
