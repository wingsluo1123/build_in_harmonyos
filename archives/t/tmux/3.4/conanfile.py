from conan import ConanFile
from conan.tools.autotools import AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
import os


class TmuxConan(ConanFile):
    name = "tmux"
    version = "3.4"

    license = "ISC"
    url = "https://github.com/tmux/tmux"
    homepage = "https://github.com/tmux/tmux"
    description = "tmux is a terminal multiplexer"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")
        self.requires("libevent/2.1.12")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
        ])

        libevent = self.dependencies["libevent"]
        ncurses = self.dependencies["ncurses"]

        event_include = ":".join(libevent.cpp_info.includedirs)
        event_libdir = ":".join(libevent.cpp_info.libdirs)

        tc.configure_args.append(
            f"EVENT_CFLAGS=-I{event_include}"
        )
        tc.configure_args.append(
            f"EVENT_LIBS=-L{event_libdir} -levent_core -levent_extra"
        )

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
