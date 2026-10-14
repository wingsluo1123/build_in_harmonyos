#!/usr/bin/env python3
"""Conan recipe — libglvnd 1.7.0 (Meson).

libglvnd is the vendor-neutral OpenGL / OpenGL ES dispatch layer: it
exposes the public GL entry points and forwards them to the vendor
driver selected at run time (GLVND = GL Vendor-Neutral Dispatch).

OHOS notes
----------
* OpenHarmony ships /system/lib64/libEGL.so. libEGL is therefore built as
  a static archive (patches/0001) so the package cannot shadow the system
  loader (iron rule R26).
* Entrypoint patching is disabled: OHOS refuses mprotect(PROT_EXEC) on
  file-backed private mappings (W^X), so __glDispatchPatchCallbacks can
  never install a vendor patch table. The upstream tests that exercise
  patching detect this themselves and return the "skip" code (77) — they
  are not modified or removed.
* X11/GLX are disabled because OHOS has no X server.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.meson import Meson, MesonToolchain


class LibglvndConan(ConanFile):
    name = "libglvnd"
    version = "1.7.0"
    description = "The GL Vendor-Neutral Dispatch library (OpenGL/OpenGL ES/EGL dispatch layer)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/glvnd/libglvnd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libglvnd/1.7.0 is packaged for Linux/OHOS only."
            )

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS has no X server: drop the X11/GLX backends entirely.
        tc.project_options["x11"] = "disabled"
        tc.project_options["glx"] = "disabled"
        # W^X: mprotect(PROT_EXEC) on file-backed mappings is denied, so the
        # patching ABI cannot work. Disabling it makes the related upstream
        # tests self-skip instead of reporting a spurious failure.
        tc.project_options["entrypoint-patching"] = "disabled"
        tc.generate()
        # E481: the OHOS profile only names clang, so Meson cannot resolve
        # ar/ranlib for the native file and the archive steps fail.
        self._inject_llvm_archiver_tools()

    def build(self):
        # E481: the OHOS worker has no usable /tmp; clang and ninja fail to
        # create temporary files unless TMPDIR points inside the build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── Upstream official test suite (mandatory) ──
        if not cross_building(self) and can_run(self):
            meson.test()

    def _inject_llvm_archiver_tools(self):
        """Pin ar/ranlib into the Meson native file when the profile omits them."""
        machine_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(machine_file):
            return
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        search_dirs = [bindir, "/data/service/hnp/bin"]
        for directory in search_dirs:
            if not directory:
                continue
            if not ar:
                candidate = os.path.join(directory, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(directory, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate
        if not ar and not ranlib:
            return
        with open(machine_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        insert = []
        if ar and "\nar =" not in content:
            insert.append(f"ar = '{ar}'")
        if ranlib and "\nranlib =" not in content:
            insert.append(f"ranlib = '{ranlib}'")
        if not insert:
            return
        content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
        with open(machine_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def package(self):
        meson = Meson(self)
        meson.install()
        if self.settings.os == "OHOS":
            # OHOS refuses to dlopen an unsigned ELF: the loader reports
            # EACCES unless the object carries a .codesign blob. Sign every
            # shared object we ship so consumers can actually load it.
            self._sign_installed_elfs()
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=self.package_folder,
        )

    def _sign_installed_elfs(self):
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS ELF signing tool not found: {tool}")
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets.extend(
                path
                for path in glob.glob(os.path.join(self.package_folder, "lib", pattern))
                if os.path.isfile(path) and not os.path.islink(path)
            )
        for target in targets:
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')

    def package_info(self):
        # libEGL is shipped as a static archive (see patches/0001) to avoid
        # clashing with /system/lib64/libEGL.so.
        self.cpp_info.libs = [
            "GLdispatch",
            "GLESv1_CM",
            "GLESv2",
            "OpenGL",
            "EGL",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libglvnd")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
