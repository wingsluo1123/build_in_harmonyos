#!/usr/bin/env python3
"""Conan recipe for PAPPL 1.4.12 (Printer Application Framework) using Autotools.

PAPPL is the C framework for CUPS Printer Applications. The recipe builds the
static library and runs the upstream test suite (testhttpmon / testpappl /
testmainloop) inside build().

Platform notes (OHOS):
- bionic lacks pthread_cancel/pthread_setcancelstate -> patch 0001 adds
  AC_CHECK_FUNCS detection and guards the USB gadget call sites.
- DNS-SD uses pappl's Avahi code path against the avahi-client and
  avahi-common libraries shipped by the avahi-compat-libdns_sd package (an
  avahi-client.pc shim maps the conan package name); without an avahi daemon
  at runtime, registrations degrade to logged errors by design.
- pkg-config shims map the conan package names libpng1.6/libusb to the
  upstream module names libpng16/libusb-1.0 that pappl's configure probes.
- autoconf is taken from the environment (harmonybrew on the device, SDK on
  CI workers); configure.ac regeneration with "autoconf -f" is sanctioned by
  the note at the top of configure.ac.
"""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PapplConan(ConanFile):
    name = "pappl"
    version = "1.4.12"
    description = "Printer Application Framework for CUPS Printer Applications"
    license = "Apache-2.0"
    homepage = "https://www.msweet.org/pappl/"
    url = "https://github.com/michaelrsweet/pappl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Declaration order shapes the static link line (leaf libraries first).
        self.requires("openssl/3.5.6")
        self.requires("avahi-compat-libdns_sd/0.9_rc5")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng1.6/1.6.58")
        self.requires("libusb/1.0.27")
        self.requires("cups/2.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        for source in self.conan_data["sources"]:
            try:
                get(self, filename="pappl-1.4.12.tar.gz", **source, strip_root=True)
                break
            except Exception:
                if source is self.conan_data["sources"][-1]:
                    raise

    @property
    def _shell(self):
        return "/system/bin/sh" if self.settings.os == "OHOS" else "/bin/sh"

    @property
    def _tmpdir(self):
        if self.settings.os == "OHOS":
            # Keep autoconf/libc scratch off HMDFS (setgid dirs + umask traps).
            candidate = "/data/storage/el2/base/cache/pappl"
            try:
                os.makedirs(candidate, exist_ok=True)
                return candidate
            except OSError:
                return os.environ.get("TMPDIR") or "/data/storage/el2/base/cache"
        return os.path.join(self.build_folder, "tmp")

    def _write_pkg_config_shims(self):
        """Map conan package names to the upstream modules pappl probes."""
        pc_dir = os.path.join(self.generators_folder, "pkgconfig-shim")
        os.makedirs(pc_dir, exist_ok=True)

        # Simple name shims resolved through conan-generated pc files.
        shims = [
            ("libpng16.pc", "libpng16", "libpng (Conan name shim)", "libpng"),
            ("libusb-1.0.pc", "libusb-1.0", "libusb (Conan name shim)", "libusb"),
        ]
        for filename, module, description, requirement in shims:
            with open(os.path.join(pc_dir, filename), "w", encoding="utf-8") as handle:
                handle.write("Name: %s\n" % module)
                handle.write("Description: %s\n" % description)
                handle.write("Version: 1.0\n")
                handle.write("Requires: %s\n" % requirement)

        # avahi-client: the avahi-compat-libdns_sd package ships libavahi-client
        # and libavahi-common, but only under its own pc name. pappl's DNS-SD
        # support probes the "avahi-client" module (HAVE_AVAHI code path).
        avahi = self.dependencies["avahi-compat-libdns_sd"]
        with open(os.path.join(pc_dir, "avahi-client.pc"), "w", encoding="utf-8") as handle:
            handle.write("prefix=%s\n" % avahi.package_folder)
            handle.write("libdir=${prefix}/lib\n")
            handle.write("includedir=${prefix}/include\n")
            handle.write("Name: avahi-client\n")
            handle.write("Description: Avahi client library (Conan shim)\n")
            handle.write("Version: 0.9\n")
            handle.write("Libs: -L${libdir} -lavahi-client -lavahi-common\n")
            handle.write("Cflags: -I${includedir}\n")
        return pc_dir

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._write_pkg_config_shims()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-tls=openssl",
            "--disable-shared",
            "--enable-static",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

        # configure runs conftest binaries that link shared dependencies
        # (libexpat.so.1, libpng16.so, libusb-1.0.so, ...); expose their
        # libdirs to the loader for the whole build.
        env = Environment()
        libpaths = []
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                libpaths.append(os.path.join(dep.package_folder, libdir))
        if libpaths:
            for libpath in dict.fromkeys(libpaths):
                env.prepend_path("LD_LIBRARY_PATH", libpath)
        env.vars(self).save_script("pappl_build_env")

    @property
    def _conf_env_prefix(self):
        shim = os.path.join(self.generators_folder, "pkgconfig-shim")
        return (
            'CONFIG_SHELL="{shell}" SHELL="{shell}" TMPDIR="{tmpdir}" '
            'PKG_CONFIG_PATH="{gens}:{shim}:$PKG_CONFIG_PATH"'
        ).format(shell=self._shell, tmpdir=self._tmpdir,
                 gens=self.generators_folder, shim=shim)

    def _configure(self):
        command = "%s %s ./configure %s" % (
            self._conf_env_prefix,
            self._shell,
            " ".join(["--prefix=%s" % self.package_folder,
                      "--with-tls=openssl",
                      "--disable-shared",
                      "--enable-static",
                      "--build=aarch64-unknown-linux-gnu",
                      "--host=aarch64-unknown-linux-gnu"]),
        )
        self.run(command, cwd=self.source_folder, env="conanbuild")

    def _make(self, *args):
        self.run('make -j1 SHELL="%s" %s' % (self._shell, " ".join(args)),
                 cwd=self.source_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # configure.ac gained AC_CHECK_FUNCS guards; regenerate with the
        # upstream-sanctioned "autoconf -f".
        self.run("autoconf -f", cwd=self.source_folder, env="conanbuild")
        # Autoconf's confXXXXXX scratch dirs get mode 0700 via "umask 077";
        # on HMDFS (setgid directories) that combination makes config.status
        # fail creating subs1.awk (E011/E129). Relax to 022 - the scratch only
        # holds generated makefile fragments.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        '(umask 077 && mktemp -d "./confXXXXXX")',
                        '(umask 022 && mktemp -d "./confXXXXXX")')
        self._configure()
        self._make("all")
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        testsuite = os.path.join(self.source_folder, "testsuite")
        tmpdir = self._tmpdir

        # 1) Canonical upstream "make test" target: testhttpmon plus testpappl
        #    with the upstream category list (api,client,pwg-raster).
        self.run(
            'cd %s && TMPDIR=%s TEMP=%s timeout 1500 make -j1 SHELL="%s" test; '
            'rc=$?; echo PAPPL_MAKE_TEST_RC=$rc; test $rc -eq 0'
            % (testsuite, tmpdir, tmpdir, self._shell),
            env="conanbuild",
        )

        # 2) The optional "-t all" sweep (jpeg/png image tests + client-10x1000
        #    stress) is intentionally NOT run in build(): together with the
        #    canonical "make test" above it exceeds the CI worker's 3600s
        #    conan-create budget (observed elapsedTime=3634s -> KILL).  It was
        #    validated locally on the device; if a fuller sweep is needed, add a
        #    package timeout override rather than changing this recipe.

        # 3) testmainloop smoke: exercise the papplMainloop CLI surface.
        self.run(
            'cd %s && TMPDIR=%s TEMP=%s timeout 120 ./testmainloop --version; '
            'rc=$?; echo TESTMAINLOOP_RC=$rc; test $rc -eq 0'
            % (testsuite, tmpdir, tmpdir),
            env="conanbuild",
        )

    def package(self):
        staging = os.path.join(self.build_folder, "stage")
        os.makedirs(staging, exist_ok=True)
        self._make("install BUILDROOT=%s" % staging)
        root = os.path.join(staging, self.package_folder.strip("/"))
        copy(self, "libpappl.a", os.path.join(root, "lib"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(root, "include", "pappl"),
             os.path.join(self.package_folder, "include", "pappl"))
        copy(self, "pappl.pc", os.path.join(root, "lib", "pkgconfig"),
             os.path.join(self.package_folder, "lib", "pkgconfig"))
        copy(self, "*", os.path.join(root, "share", "pappl"),
             os.path.join(self.package_folder, "share", "pappl"))

    def package_info(self):
        self.cpp_info.libs = ["pappl"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.cpp_info.requires = [
            "openssl::openssl",
            "avahi-compat-libdns_sd::avahi-compat-libdns_sd",
            "libjpeg-turbo::libjpeg-turbo",
            "libpng1.6::libpng1.6",
            "libusb::libusb",
            "cups::cups",
        ]
        self.cpp_info.set_property("cmake_file_name", "pappl")
        self.cpp_info.set_property("cmake_target_name", "pappl::pappl")
        self.cpp_info.set_property("pkg_config_name", "pappl")
