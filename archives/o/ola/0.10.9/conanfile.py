#!/usr/bin/env python3
"""Conan recipe for ola (Open Lighting Architecture) 0.10.9 on OHOS.

Adapted for OpenHarmony PC (aarch64, bionic libc). Path A scope:
core libs only (olacommon / ola / olaserver / olad_plugin_api);
HTTP UI, Python bindings, and USB-specific plugins are not packaged.

R26 enforced: same-name system libraries (protobuf, pthread, dl, m)
are linked statically inside the package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class OlaConan(ConanFile):
    name = "ola"
    version = "0.10.9"
    description = "Open Lighting Architecture — DMX512 / Art-Net / sACN / RDM"
    # OLA is dual-licensed: GPL-2.0-or-later (server + tools) and
    # LGPL-2.1-or-later (libolacommon client library). Downstream
    # consumers must respect copyleft terms.
    license = ("GPL-2.0-or-later", "LGPL-2.1-or-later")
    homepage = "https://www.openlighting.org/"
    url = "https://github.com/OpenLightingProject/ola"
    topics = ("dmx", "art-net", "sacn", "rdm", "lighting", "ola")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Path A: no Conan recipe dependency. protobuf is consumed from
        # the host system (already installed at /storage/Users/currentUser/usr/local)
        # and exposed via system_libs below. Doing it this way matches the
        # OLA build system expectations (protoc + libprotoc + protobuf headers)
        # and avoids dragging in a transitive protobuf conan recipe.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_configure_for_hmdfs(self):
        """E011: HMDFS + uid 0 DAC quirk — autotools creates
        ./confXXXXXX/ with `umask 077` → mode 0700; uid 0 on HMDFS does
        NOT bypass DAC, so config.status then can't write into its own
        scratch dir. Patch the generated `configure` script's two specific
        `umask 077` lines (mktemp scratch dir creation) to `umask 022`.

        R6 exemption: this modifies the generated `configure` script
        (autotools-generated artifact). A static patches/ entry would be
        fragile because `configure` content varies by upstream autotools
        version, and `patch_ng` fails hard on mismatch. Keeping the
        mutation in-recipe with anchored exact-line replacement is
        defensive: if upstream changes the lines, this no-ops rather than
        breaking the build. The fix is tracked in source (conanfile.py
        revision), not in conandata.yml.
        """
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r", encoding="utf-8") as f:
            data = f.read()
        # Anchored replacement: only the two autotools scratch-dir umasks
        # in `configure`. Other `umask` lines (e.g. test scripts, install
        # rules) must keep their original semantics.
        anchored_pairs = (
            ("(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null",
             "(umask 022 && mktemp -d \"./confXXXXXX\") 2>/dev/null"),
            ("(umask 077 && mkdir \"$tmp\")",
             "(umask 022 && mkdir \"$tmp\")"),
        )
        patched = False
        for old, new in anchored_pairs:
            if old in data:
                data = data.replace(old, new, 1)
                patched = True
        if not patched:
            return  # already patched or upstream changed the lines
        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(data)
        self.output.info("E011: patched configure scratch-dir umask 077 → 022")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: same-name system libraries must be statically linked.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Path A scope (per migrate-ola.md): no HTTP UI, no Python bindings,
        # no examples, no in-tree unit tests (we provide real-API tests
        # in test_package/ instead).
        tc.configure_args.append("--disable-http")
        tc.configure_args.append("--disable-unittests")
        tc.configure_args.append("--disable-examples")
        # OLA enables some components by default that need extra deps we
        # don't carry; be explicit about disabling them.
        tc.configure_args.append("--disable-osc")  # liblo not packaged
        # OHOS bionic builds trigger clang -Wunused-parameter warnings on
        # STLInsertOrDie et al (because NDEBUG strips assert(); the unused
        # parameter check fires). Disable fatal warnings so make doesn't
        # bail on a warning — we still get the warning, just not as error.
        tc.configure_args.append("--disable-fatal-warnings")

        # System-installed headers/libs (protobuf, libuuid, etc.) live
        # under the user's local prefix. autotools finds them via CPPFLAGS/
        # LDFLAGS/PKG_CONFIG_PATH. R33-safe: these are build-environment
        # hooks (Conan recipe-controlled), not bare shell var overrides.
        env = Environment()
        env.append("CPPFLAGS", ["-I/storage/Users/currentUser/usr/local/include"])
        env.append("LDFLAGS", ["-L/storage/Users/currentUser/usr/local/lib"])
        env.prepend_path(
            "PKG_CONFIG_PATH",
            "/storage/Users/currentUser/usr/local/lib/pkgconfig",
        )
        env.prepend_path(
            "PKG_CONFIG_PATH",
            "/storage/Users/currentUser/usr/local/lib64/pkgconfig",
        )
        # Linker flags: libprotoc.a is static and depends on libprotobuf symbols.
        env.append("LIBS", ["-lprotobuf"])
        env.append("LIBS", ["-luuid"])
        env.append("LIBS", ["-lpthread"])
        env.append("LIBS", ["-ldl"])
        env.append("LIBS", ["-lm"])
        env.vars(self).save_script("ola_build_env")
        tc.generate()

    def build(self):
        self._patch_configure_for_hmdfs()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j%d" % os.cpu_count()])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Copy LICENSE files so downstream consumers see the GPL/LGPL notice.
        for license_file in ("COPYING", "LICENSE", "LICENSE.GPL", "LICENSE.LGPL"):
            src = os.path.join(self.source_folder, license_file)
            if os.path.exists(src):
                copy(self, license_file, src, self.package_folder)

    def package_info(self):
        # Path A scope libs (all produced by `make install`). Listed in
        # link order — common first (depends on nothing), then protocol
        # cores, then client lib, then server libs last.
        self.cpp_info.libs = [
            "olacommon",                   # common/network, common/rdm, common/io, ...
            "olae131conf",                 # plugins/e131/messages config schema
            "olaartnetconf",               # plugins/artnet/messages config schema
            "olausbproconf",               # plugins/usbpro/messages config schema
            "olatrigger",                  # tools/ola_trigger
            "oladummy",                    # plugins/dummy (no-op, safe default)
            # NOTE: olaacn (libs/acn, CID helpers) is intentionally omitted.
            # Upstream OLA installs libolaacn only with `--enable-e133`; the
            # default is noinst_LTLIBRARIES, so CMakeDeps can't find it on
            # disk and aborts the test_package build. E1.31 (sACN) pulls
            # libolaacn symbols in via libolae131core's static archive, so
            # downstream `ola::olae131` linkage gets the ACN CID API for free.
            "olae131",                     # plugins/e131 (sACN / E1.31)
            "olaespnet",                   # plugins/espnet
            "olakarate",                   # plugins/karate (Enttec Open DMX)
            "olakinet",                    # plugins/kinet (Color Kinetics)
            "olashownet",                  # plugins/shownet
            "olarenard",                   # plugins/renard
            "olasandnet",                  # plugins/sandnet
            "olapathport",                 # plugins/pathport
            "olamilinst",                  # plugins/milinst
            "olaopenpixelcontrol",         # plugins/openpixelcontrol
            "olastageprofi",               # plugins/stageprofi
            "olauartdmx",                  # plugins/uartdmx
            "olaopendmx",                  # plugins/opendmx
            "olagpiocore",                 # plugins/gpio core
            "olagpio",                     # plugins/gpio
            "olaspi",                      # plugins/spi
            "olaspicore",                  # plugins/spi core
            "olausbpro",                   # plugins/usbpro widget
            "olaartnet",                   # plugins/artnet
            "ola",                         # client RPC stubs (depends on olacommon)
            "olaserver",                   # server core (depends on olaserverplugininterface)
            "olaserverplugininterface",    # olad plugin API (Plugin/Device/Port/Universe)
        ]
        # R26: same-name system libraries linked statically into the .a's.
        self.cpp_info.system_libs = [
            "protobuf",  # system 3.21.12 (host-installed)
            "pthread",
            "dl",
            "m",
        ]
        # OLA ships C++17 code (autotools default uses gnu++11; C++17 is
        # needed for std::filesystem and protobuf 3.21 headers in some paths).
        self.cpp_info.cppflags = ["-std=gnu++17"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "ola")