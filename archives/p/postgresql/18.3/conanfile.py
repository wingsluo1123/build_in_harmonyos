from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class PostgresqlConan(ConanFile):
    name = "postgresql"
    version = "18.3"
    description = "PostgreSQL is a powerful, open source object-relational database system"
    license = "PostgreSQL"
    homepage = "https://www.postgresql.org/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-icu",
            "--without-readline",
            "--without-zlib",
            "--without-openssl",
        ])
        if self.settings.os in ("Linux", "OHOS"):
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: OHOS /tmp is read-only, use build folder for temp files
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        # Fix umask for hmdfs filesystem (E046: hmdfs creates dirs with 077 umask)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pq", "pgcommon", "pgport"]
        self.cpp_info.includedirs = [
            "include",
            "include/postgresql",
            "include/postgresql/server",
            "include/postgresql/internal",
        ]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "lib/postgresql"]
