#!/usr/bin/env python3
"""Conan recipe — gst-plugins-base 1.28.3 (meson)

GStreamer base plugins and supporting libraries (app, audio, fft, pbutils,
riff, rtp, rtsp, sdp, tag, video, allocators, controller).

Dependencies:
  - gstreamer/1.28.3 (local archives, not yet published to remote)
  - glib/2.84.0.1 (conan remote)

R32: settings.os check uses in ("Linux", "OHOS")
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins and supporting libraries"
    license = "LGPL-2.0-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("glib/2.84.0.1")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gst-plugins-base is only supported on Linux and OHOS"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["iso-codes"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["vorbis"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["ogg"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.generate()
        self._inject_meson_archive_tools()

    def _inject_meson_archive_tools(self):
        """Inject ar/ranlib/pkg-config into Meson native/cross files.

        MesonToolchain omits ar/ranlib; cross builds also omit pkg-config.
        Without these, Meson reports "Found pkg-config: NO" and cannot
        see PkgConfigDeps .pc files, and may fail to find llvm-ar when
        the compiler is in /data/service/hnp/bin (not on PATH).
        """
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if (
                pkg_config
                and "\npkg-config =" not in content
                and "\npkgconfig =" not in content
            ):
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace(
                "[binaries]\n",
                "[binaries]\n" + "\n".join(extras) + "\n",
                1,
            )
            with open(nf, "w") as f:
                f.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """Re-sign .so files after meson install rewrites rpath (OHOS XPM)."""
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c") or ""
        candidates_objcopy = []
        if cc:
            candidates_objcopy.append(
                os.path.join(os.path.dirname(cc), "llvm-objcopy")
            )
        candidates_objcopy += [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        objcopy = next(
            (p for p in candidates_objcopy if p and os.path.isfile(p)), None
        )
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skip OHOS codesign (cross/SDK env)"
            )
            return
        for so in sos:
            if os.path.islink(so):
                continue
            if objcopy:
                self.run(
                    '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                        oc=objcopy, f=so
                    )
                )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=so
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gst-plugins-base")
        self.cpp_info.set_property("pkg_config_name", "gstreamer-plugins-base-1.0")

        self.cpp_info.libs = [
            "gstapp-1.0",
            "gstaudio-1.0",
            "gstfft-1.0",
            "gstpbutils-1.0",
            "gstriff-1.0",
            "gstrtp-1.0",
            "gstrtsp-1.0",
            "gstsdp-1.0",
            "gsttag-1.0",
            "gstvideo-1.0",
            "gstallocators-1.0",
            "gstcontroller-1.0",
        ]
        self.cpp_info.includedirs = ["include", "include/gstreamer-1.0"]
        # GStreamer plugin .so files are installed under lib/gstreamer-1.0/
        self.cpp_info.bindirs = ["lib/gstreamer-1.0"]

        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
