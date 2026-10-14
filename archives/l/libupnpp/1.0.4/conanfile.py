import os
import io
import shlex
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, unzip
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibupnppConan(ConanFile):
    name = "libupnpp"
    version = "1.0.4"
    description = "C++ UPnP device and control-point wrapper"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.lesbonscomptes.com/upmpdcli/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "use_expat": [True, False]}
    default_options = {"shared": True, "fPIC": True, "use_expat": False}

    def export_sources(self):
        copy(self, "*", src=os.path.join(self.recipe_folder, "upstream_support"),
             dst=os.path.join(self.export_sources_folder, "upstream_support"))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This recipe requires a POSIX target")

    def requirements(self):
        self.requires("libnpupnp/6.2.3", transitive_headers=True, transitive_libs=True)
        # Keep the same curl reference as the released libnpupnp recipe.
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)
        if self.options.use_expat:
            self.requires("expat/2.8.5")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        # The released 1.13.2 binary hardcodes an HNP bash path which is not
        # present on all native machines. Use the published portable build.
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        archive = self.conf.get("user.libupnpp:source_archive", default=None)
        if archive:
            check_sha256(self, archive, data["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **data, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        # OHOS Python cannot reliably posix_spawn bare executable names, even
        # when a shell resolves the same names. Bind real absolute tool paths.
        with VirtualBuildEnv(self, auto_generate=True).vars().apply():
            toolchain.ar = self._tool("ar", ("llvm-ar", "ar"))
            toolchain.pkgconfig = self._tool("pkgconfig", ("pkgconf", "pkg-config"))
            ninja = self._tool("ninja", ("ninja", "ninja-build"))
        tool_environment = Environment()
        tool_environment.define("NINJA", ninja)
        tool_environment.vars(self).save_script("meson_native_tools")
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        toolchain.project_options["use_expat"] = bool(self.options.use_expat)
        toolchain.generate()

    def _tool(self, kind, names):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        explicit = self.conf.get("tools.gnu:pkg_config", default=None) if kind == "pkgconfig" else compilers.get(kind)
        compiler = compilers.get("cpp") or compilers.get("c")
        candidates = [explicit] if explicit else []
        if not explicit and compiler and kind == "ar":
            suffix = re.search(r"clang(?:\+\+)?(-[0-9]+)?$", os.path.basename(compiler))
            for name in names:
                if suffix and suffix.group(1) and name.startswith("llvm-"):
                    candidates.append(os.path.join(os.path.dirname(compiler), name + suffix.group(1)))
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        if not explicit:
            candidates.extend(names)
        for candidate in candidates:
            resolved = candidate if os.path.isabs(candidate) else shutil.which(candidate)
            if resolved and os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return os.path.abspath(resolved)
        raise ConanInvalidConfiguration("Required {} executable unavailable: {}".format(kind, candidates))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()
        # The release also contains a self-test behind TEST_BASE64 which is
        # not registered by Meson. Keep its original main and all eight cases.
        cpp = self.conf.get("tools.build:compiler_executables", default={}).get("cpp", "c++")
        test = os.path.join(self.build_folder, "upstream_base64")
        arguments = [cpp, "-std=c++17", "-DTEST_BASE64", "-DNDEBUG",
                     "-I" + os.path.join(self.source_folder, "upstream_support"),
                     "-I" + os.path.join(self.source_folder, "libupnpp"),
                     os.path.join(self.source_folder, "libupnpp", "base64.cxx"),
                     "-o", test]
        self.run(" ".join(shlex.quote(x) for x in arguments))
        self.run(shlex.quote(test) + " -i")
        self.output.info("LIBUPNPP_UPSTREAM_RESULT=1/1; original_vectors=8; PASS")

    def package(self):
        Meson(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            # HMDFS aliases can be read by normal filesystem APIs but rejected
            # by the native loader. Validate the entire chain before replacing
            # only our two aliases with identical, mode-preserving real files.
            library = os.path.join(self.package_folder, "lib", "libupnpp.so." + self.version)
            aliases = [os.path.join(self.package_folder, "lib", name)
                       for name in ("libupnpp.so.17", "libupnpp.so")]
            if not os.path.isfile(library) or os.path.islink(library):
                raise ConanInvalidConfiguration("Expected one real versioned libupnpp library")
            for alias in aliases:
                if not os.path.islink(alias) or not os.path.samefile(alias, library):
                    raise ConanInvalidConfiguration("Unexpected installed shared-library alias: " + alias)
            for alias in aliases:
                os.unlink(alias)
                shutil.copy2(library, alias)
                with open(library, "rb") as source, open(alias, "rb") as target:
                    if source.read() != target.read():
                        raise ConanInvalidConfiguration("Shared-library alias byte drift")
            for installed in [library] + aliases:
                self._resign_installed(installed)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _resign_installed(self, library):
        with VirtualBuildEnv(self, auto_generate=True).vars().apply():
            objcopy = self._tool("objcopy", ("llvm-objcopy",))
            readelf = self._tool("readelf", ("llvm-readelf",))
            signer = self._tool("signer", ("binary-sign-tool",))
        unsigned, signed = library + ".unsigned", library + ".signed"
        if os.path.lexists(unsigned) or os.path.lexists(signed):
            raise ConanInvalidConfiguration("Stale signing temporary beside " + library)
        def section_count(path):
            output = io.StringIO()
            self.run(shlex.join([readelf, "-S", path]), stdout=output)
            return sum(".codesign" in line for line in output.getvalue().splitlines())
        if section_count(library) > 1:
            raise ConanInvalidConfiguration("Duplicate code-sign sections")
        try:
            shutil.copy2(library, unsigned)
            self.run(shlex.join([objcopy, "--remove-section", ".codesign", unsigned]))
            if section_count(unsigned):
                raise ConanInvalidConfiguration("Old code-sign section was not removed")
            self.run(shlex.join([signer, "sign", "-inFile", unsigned,
                                 "-outFile", signed, "-selfSign", "1"]), stdout=sys.stderr)
            if not os.path.isfile(signed) or section_count(signed) != 1:
                raise ConanInvalidConfiguration("Signed installed library is invalid")
            os.chmod(signed, 0o755)
            os.replace(signed, library)
        finally:
            for temporary in (unsigned, signed):
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def package_info(self):
        self.cpp_info.libs = ["upnpp"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "libupnpp")
        self.cpp_info.set_property("cmake_target_name", "libupnpp::libupnpp")
        self.cpp_info.set_property("pkg_config_name", "libupnpp")
