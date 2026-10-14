import os
import shlex
from pathlib import Path
from conan import ConanFile
from conan.tools.files import replace_in_file
from conan.tools.files import copy, get, rm, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualRunEnv


class LibunibreakConan(ConanFile):
    name = "libunibreak"
    version = "8.0"
    package_type = "library"
    license = "Zlib"
    homepage = "https://github.com/adah1972/libunibreak"
    description = "Unicode line, word and grapheme segmentation"
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

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        archive = os.environ.get("LIBUNIBREAK_SOURCE_ARCHIVE")
        if archive:
            source["url"] = Path(archive).resolve(strict=True).as_uri()
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static"])
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def _configure_tmpdir(self):
        # HMDFS preserves creation-time access semantics; chmod afterward
        # cannot repair Autoconf's private 0700 temporary directories.
        configure = os.path.join(self.source_folder, "configure")
        original_stat = os.stat(configure)
        replacements = (
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 022 && mkdir "$tmp") &&'),
            ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        )
        for old, new in replacements:
            replace_in_file(self, configure, old, new, strict=True)
        os.utime(configure, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        scratch = os.path.join(self.build_folder, ".autoconf-tmp")
        previous = os.umask(0o022)
        try:
            os.mkdir(scratch, mode=0o755)
        finally:
            os.umask(previous)
        return scratch

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            guess = os.path.join(self.source_folder, "config.guess")
            sub = os.path.join(self.source_folder, "config.sub")
            self.run('sh "' + guess + '"')
            self.run('sh "' + sub + '" aarch64-unknown-linux-ohos')
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            scratch = self._configure_tmpdir()
            # Prefix after Conan activation, so the ambient TMPDIR cannot win.
            configure = shlex.quote(os.path.join(self.source_folder, "configure"))
            self.run("TMPDIR=" + shlex.quote(scratch) + " sh " + configure +
                     " " + autotools._configure_args, env=["conanbuild", "conanrun"])
        else:
            autotools.configure()
        autotools.make(args=["-j2"])
        # All three unchanged official Unicode conformance suites.
        # Upstream's custom check rule duplicates check_PROGRAMS prerequisites;
        # parallel check can compile tests-tests.o twice into the same .Tpo.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "LICENCE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["unibreak"]
        self.cpp_info.set_property("cmake_file_name", "libunibreak")
        self.cpp_info.set_property("cmake_target_name", "libunibreak::libunibreak")
        self.cpp_info.set_property("pkg_config_name", "libunibreak")
