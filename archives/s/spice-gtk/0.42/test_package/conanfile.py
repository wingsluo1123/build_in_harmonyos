import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("spice-protocol/0.14.5")
        self.requires("glib/2.84.0")
        self.requires("pixman/0.46.4.1")
        self.requires("openssl/3.5.6")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("zlib/1.3.1")
        self.requires("json-glib/1.6.6")
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")

    def build(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        includes = []
        libdirs = []
        tested_libs = []
        dependency_libs = []
        system_libs = []
        link_flags = []
        tested_dep = self.dependencies["spice-gtk"]
        tested_ref = tested_dep.ref
        for _ref, dependency in self.dependencies.items():
            infos = [dependency.cpp_info] + list(dependency.cpp_info.components.values())
            for info in infos:
                includes.extend(info.includedirs)
                libdirs.extend(info.libdirs)
                system_libs.extend(info.system_libs)
                link_flags.extend(info.sharedlinkflags)
                link_flags.extend(info.exelinkflags)
                if dependency.ref == tested_ref:
                    tested_libs.extend(info.libs)
                else:
                    dependency_libs.extend(info.libs)

        def unique(items):
            seen = set()
            result = []
            for item in items:
                if item and item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        include_flags = " ".join(f'-I"{path}"' for path in unique(includes))
        libdir_flags = " ".join(f'-L"{path}"' for path in unique(libdirs))
        lib_flags = " ".join(
            f"-l{name}" for name in unique(tested_libs + dependency_libs + system_libs)
        )
        extra_link_flags = " ".join(unique(link_flags))
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = executables.get("c")
        if not cc:
            raise ConanException("C compiler not found in tools.build:compiler_executables")
        test_source = os.path.join(self.source_folder, "test_spice_gtk.c")
        defines = ""
        if "spice-client-gtk-3.0" in tested_dep.cpp_info.libs:
            defines = "-DSPICE_GTK_TEST_WITH_GTK=1"
        self.run(
            f'{cc} "{test_source}" -o test_spice_gtk '
            f"{defines} {include_flags} {libdir_flags} {lib_flags} {extra_link_flags}"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link test completed")
            return
        self.run("./test_spice_gtk", env="conanrun")
