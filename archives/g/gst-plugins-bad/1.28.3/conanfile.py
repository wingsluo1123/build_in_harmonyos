#!/usr/bin/env python3
"""Conan recipe for gst-plugins-bad 1.28.3 (GStreamer monorepo).

This recipe builds gst-plugins-bad from the GStreamer monorepo, which also
builds gstreamer core and gst-plugins-base as meson subprojects.
GStreamer 1.28.x uses a monorepo structure where all modules are in a single
repository, so we build from the monorepo root.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os


class GstPluginsBadConan(ConanFile):
    name = "gst-plugins-bad"
    version = "1.28.3"
    description = "GStreamer Bad Plug-ins (multimedia framework, monorepo build)"
    license = "LGPL-2.0-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GStreamer monorepo builds glib as a meson subproject fallback;
        # however, if system glib is available (cmd-pkgs), it is preferred.
        # No conan package dependencies — all subprojects are built from source.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Monorepo build options
        tc.project_options["base"] = "enabled"
        tc.project_options["bad"] = "enabled"
        tc.project_options["good"] = "disabled"
        tc.project_options["ugly"] = "disabled"
        tc.project_options["libav"] = "disabled"
        tc.project_options["devtools"] = "disabled"
        tc.project_options["ges"] = "disabled"
        tc.project_options["rtsp_server"] = "disabled"
        tc.project_options["python"] = "disabled"
        tc.project_options["sharp"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tls"] = "disabled"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["gpl"] = "disabled"
        tc.project_options["gst-full"] = "disabled"
        # Use system glib (from cmd-pkgs) if available; otherwise meson will
        # download glib.wrap from wrapdb automatically (wrap_mode=default)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # Fix: Ensure correct glib tools are found before broken HNP versions
        # The HNP glib-mkenums uses /usr/bin/perl which doesn't exist
        from conan.tools.files import load, save
        import re
        native_file = os.path.join(self.generators_folder, tc.native_filename or "conan_meson_native.ini")
        content = load(self, native_file)
        if "ar = " not in content:
            content = content.replace("[binaries]\nc = ", "[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\nc = ")
        # Add glib-mkenums to binaries section to override broken HNP version
        if "glib-mkenums = " not in content:
            content = content.replace("[binaries]\n", "[binaries]\nglib-mkenums = '/storage/Users/currentUser/usr/local/bin/glib-mkenums'\n")
        # Add system pkg-config path so meson finds system-installed glib
        system_pkgconfig = "/storage/Users/currentUser/usr/local/lib/pkgconfig"
        if system_pkgconfig not in content:
            content = re.sub(
                r"pkg_config_path = '([^']+)'",
                f"pkg_config_path = ['{system_pkgconfig}', '\\1']",
                content
            )
        save(self, native_file, content)
        # Also fix conanbuild.sh to put correct glib path first in PATH
        build_env = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.exists(build_env):
            env_content = load(self, build_env)
            if "/storage/Users/currentUser/usr/local/bin" not in env_content.split("\n")[0]:
                env_content = "export PATH=\"/storage/Users/currentUser/usr/local/bin:$PATH\"\n" + env_content
                save(self, build_env, env_content)

    def build(self):
        apply_conandata_patches(self)
        import subprocess
        prefix = "/storage/Users/currentUser/usr/local"
        # 1. Install glib from cmd-pkgs if not present
        if not os.path.exists(f"{prefix}/lib/libglib-2.0.a"):
            self.output.info("Installing glib 2.88.0 from cmd-pkgs...")
            subprocess.run(["sh", "-c",
                "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- glib 2.88.0"],
                check=True)
        # 2. Build pcre2 from source if not present (glib dependency)
        if not os.path.exists(f"{prefix}/lib/libpcre2-8.a"):
            self.output.info("Building pcre2 from source...")
            subprocess.run(["sh", "-c",
                f"cd $TMPDIR && curl -fsSL 'https://wrapdb.mesonbuild.com/v2/pcre2_10.47-3/get_source/pcre2-10.47.tar.bz2' -o pcre2.tar.bz2 && tar xjf pcre2.tar.bz2 && cd pcre2-10.47 && mkdir -p build && cd build && cmake .. -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_INSTALL_PREFIX={prefix} -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DPCRE2_BUILD_PCRE2GREP=OFF -DPCRE2_BUILD_TESTS=OFF && make -j2 && make install"],
                check=True)
        # 3. Build libffi from source if not present (gobject dependency)
        if not os.path.exists(f"{prefix}/lib/libffi.a"):
            self.output.info("Building libffi from source...")
            subprocess.run(["sh", "-c",
                f"cd $TMPDIR && curl -fsSL 'https://gstreamer.freedesktop.org/src/mirror/libffi/libffi-meson-3.2.9999.5.tar.bz2' -o libffi.tar.bz2 && tar xjf libffi.tar.bz2 && cd libffi-meson-3.2.9999.5 && meson setup build --prefix={prefix} --buildtype=release --default-library=static && ninja -C build && ninja -C build install"],
                check=True)
        # Ensure system glib tools are found first
        os.environ["PATH"] = f"{prefix}/bin:" + os.environ.get("PATH", "")
        # Disable opensles plugin (Android-specific) by modifying meson.options
        meson_options_path = os.path.join(self.source_folder, "subprojects", "gst-plugins-bad", "meson.options")
        replace_in_file(self, meson_options_path,
                        "option('opensles', type : 'feature', value : 'auto'",
                        "option('opensles', type : 'feature', value : 'disabled'")
        # Disable gl in gst-plugins-base (requires jpeglib.h which is not available)
        gst_base_options_path = os.path.join(self.source_folder, "subprojects", "gst-plugins-base", "meson_options.txt")
        if os.path.exists(gst_base_options_path):
            replace_in_file(self, gst_base_options_path,
                            "option('gl', type : 'feature', value : 'auto'",
                            "option('gl', type : 'feature', value : 'disabled'")
        else:
            # Try meson.options (newer format)
            gst_base_options_path = os.path.join(self.source_folder, "subprojects", "gst-plugins-base", "meson.options")
            replace_in_file(self, gst_base_options_path,
                            "option('gl', type : 'feature', value : 'auto'",
                            "option('gl', type : 'feature', value : 'disabled'")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # Core gstreamer libraries
        self.cpp_info.libs = [
            "gstreamer-1.0",
            "gstbase-1.0",
            "gstcontroller-1.0",
            "gstnet-1.0",
            "gstcheck-1.0",
            # gst-plugins-base libraries
            "gstapp-1.0",
            "gstaudio-1.0",
            "gstfft-1.0",
            "gstriff-1.0",
            "gstrtp-1.0",
            "gstrtsp-1.0",
            "gstsdp-1.0",
            "gsttag-1.0",
            "gstvideo-1.0",
            "gstpbutils-1.0",
            "gstallocators-1.0",
            "gstgl-1.0",
            "gstinsertbin-1.0",
            # gst-plugins-bad libraries
            "gstadaptivedemux-1.0",
            "gstbadaudio-1.0",
            "gstbasecamerabinsrc-1.0",
            "gstcodecparsers-1.0",
            "gstcodecs-1.0",
            "gstisoff-1.0",
            "gstmpegts-1.0",
            "gstmse-1.0",
            "gstphotography-1.0",
            "gstplay-1.0",
            "gstplayer-1.0",
            "gstsctp-1.0",
            "gsttranscoder-1.0",
            "gsturidownloader-1.0",
            "gstvulkan-1.0",
            "gstwebrtc-1.0",
            "gstanalytics-1.0",
        ]
        # Add pkg-config path for downstream consumers
        self.cpp_info.set_property("pkg_config_name", "gstreamer-plugins-bad-1.0")
        self.cpp_info.set_property("cmake_target_name", "gst-plugins-bad::gst-plugins-bad")
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
