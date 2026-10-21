from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FstrcmpConan(ConanFile):
    name = "fstrcmp"
    version = "0.7.d001"
    description = "Fuzzy string comparison library (libfstrcmp)"
    license = "LGPL-3.0-or-later"
    homepage = "https://fstrcmp.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # conan 2 requires a shared option for package_type=library.
    # The upstream configure has no --enable/--disable-shared flags, so
    # AutotoolsToolchain may emit unrecognized-option warnings; harmless.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        # fstrcmp's upstream "messy" Makefile compiles with in-tree relative
        # paths (lib/downcase.c) and has no VPATH support, so this has to be an
        # in-source build: keep the build folder equal to the source folder.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "fstrcmp/0.7.d001 currently supports only OHOS armv8"
                )
            # The bundled config.sub predates HarmonyOS: 0001-config.sub-ohos.patch
            # adds the aarch64-linux-ohos triplet, which lets this build/host pair
            # be accepted.  Verified locally: config.sub aarch64-linux-ohos -> aarch64-unknown-linux-ohos.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build_requirements(self):
        # The CI worker image has no GNU libtool on PATH, but the upstream
        # configure hard-fails with "You must have GNU Libtool installed".
        # Same approach as the other autotools recipes in this repository.
        self.tool_requires("libtool/2.5.4")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # No autoreconf is needed: the shipped configure works as-is once
        # patched. Its only platform problem is that config.status creates
        # its ./confXXXXXX temp dir under umask 077, which HMDFS turns into
        # an unwritable drwx--S--- dir, so ./confXXXXXX/subs1.awk fails with
        # "Permission denied". 0002-configure-umask-022.patch fixes exactly
        # that (the same E114 workaround a52dec uses).
        autotools.configure()
        # E074: parallel make on HMDFS hits the jobserver fifo EPERM, and the
        # resource-starved CI workers then fail to fork at all
        # ("fork: Resource temporarily unavailable"). Same -j1 workaround as
        # a52dec and the abiword-plugin-* recipes.
        # all-bin deliberately excludes all-doc: etc/building.pdf needs the
        # aegis/groff toolchain and dies with Error 127 on the CI image
        # (Kodi's own tools/depends likewise builds only the library target).
        # all-bin still builds libfstrcmp plus bin/fstrcmp, bin/test_user
        # and bin/test_prelude.
        autotools.make(target="all-bin", args=["-j1"])
        # Upstream aegis/shell suite. Every tNNNN make target depends on
        # "all" (and therefore on the .pdf docs), so run the scripts exactly
        # the way the Makefile does: PATH=<pwd>/bin sh test/00/<t>.sh
        for t in ("t0001a", "t0002a", "t0003a", "t0004a", "t0005a",
                  "t0006a", "t0007a", "t0008a", "t0009a", "t0010a"):
            # TMPDIR: the suite hardcodes /tmp (read-only on the CI worker),
            # so patches/0003-test-prelude-tmpdir.patch makes it honour TMPDIR.
            self.run("PATH=$PWD/bin:$PATH TMPDIR=$PWD sh test/00/%s.sh" % t,
                     cwd=self.source_folder, env="conanbuild")

    def package(self):
        # The upstream 'install' aggregate target also installs the CLI and man/doc
        # pages (the PDF is produced by the aegis tooling), so mirror what Kodi's
        # tools/depends does: install only the header and the library/pkg-config.
        # Install straight into the package folder: AutotoolsToolchain keeps
        # --prefix=/ for the build, and "make install-*" with that prefix
        # tries to write //include, which is not writable on the CI worker
        # ("install: //include: Permission denied").
        # includedir/libdir are substituted into Makefile by configure (with
        # the toolchain's --prefix=/), so overriding prefix on the make command
        # line is not enough: they must be overridden as well.
        pkg = self.package_folder
        self.run("make install-include install-libdir -j1 prefix=%s includedir=%s/include libdir=%s/lib"
                 % (pkg, pkg, pkg),
                 cwd=self.source_folder, env="conanbuild")
        # The default option is shared=False, but libtool installs both the
        # static and the shared library. Drop the .so* like Kodi's own
        # tools/depends does, otherwise consumers link the shared object and
        # fail at run time with "Error loading shared library libfstrcmp.so.0".
        self.run("rm -f \"%s\"/lib/libfstrcmp.so*" % pkg, env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["fstrcmp"]
        self.cpp_info.set_property("pkg_config_name", "fstrcmp")
