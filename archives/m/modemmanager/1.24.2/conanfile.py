#!/usr/bin/env python3
"""Conan recipe — modemmanager 1.24.2 (ModemManager / libmm-glib, Meson).

ModemManager is the freedesktop mobile broadband modem manager. The Conan
package delivers the client-facing ``libmm-glib`` library (Mm* GObject API
over the org.freedesktop.ModemManager1 D-Bus interface) plus its headers and
generated enum/flags/error types. The ModemManager daemon itself (src/),
mmcli (cli/) and the vendor plugin stack are NOT built: they require a
running D-Bus system bus, udev + libgudev kernel device tracking and a
systemd-ish operating environment at runtime — none of which exist on
HarmonyOS PC. See notes.md for the platform adaptations.

Adapted to HarmonyOS PC (aarch64).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ModemmanagerConan(ConanFile):
    name = "modemmanager"
    version = "1.24.2"
    description = "ModemManager — mobile broadband modem management (libmm-glib client library)"
    license = "LGPL-2.1-or-later"  # libmm-glib (COPYING.LIB); the daemon would be GPL-2.0-or-later
    homepage = "https://www.freedesktop.org/wiki/Software/ModemManager/"
    url = "https://gitlab.freedesktop.org/mobile-broadband/ModemManager"
    package_type = "library"
    topics = ("modem", "mobile-broadband", "dbus", "freedesktop")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # libmm-glib is C only; drop the C++ stdlib from the package id
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # glib exposes glib-2.0/gobject-2.0/gio-2.0/gio-unix-2.0 as declared
        # components (2.84.0.1): PkgConfigDeps emits per-component .pc files
        # with proper prefixes, which meson resolves for dependency('gio-2.0')
        # and the gdbus_codegen tool variable (the non-component 2.84.0 only
        # emits a main glib-2.0.pc and meson falls back to the raw prefix=/
        # .pc shipped inside the glib package — tool variables then resolve
        # to '//bin/gdbus-codegen' and configure fails).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # dbus is configure-time only: the top-level meson.build reads the
        # interfaces_dir / system_bus_services_dir / sysconfdir variables from
        # dbus-1.pc to decide where the .xml introspection files and the bus
        # activation files are installed; no libmm-glib code links libdbus-1.
        self.requires("dbus/1.14.10", visible=False)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly (accountsservice pattern).
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._create_dbus_pc_alias()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # library-only cut (patch 0001): skip the daemon, mmcli and examples
        toolchain.project_options["daemon"] = False
        # OHOS has no udev/systemd/polkit; the daemon is not built anyway and
        # none of these are linked by libmm-glib
        toolchain.project_options["udev"] = False
        toolchain.project_options["udevdir"] = os.path.join(self.package_folder, "lib", "udev")
        toolchain.project_options["systemdsystemunitdir"] = "no"
        toolchain.project_options["systemd_suspend_resume"] = False
        toolchain.project_options["systemd_journal"] = False
        toolchain.project_options["polkit"] = "no"
        toolchain.project_options["mbim"] = False
        toolchain.project_options["qmi"] = False
        toolchain.project_options["qrtr"] = False
        # introspection needs gobject-introspection tooling; vapi needs vala
        toolchain.project_options["introspection"] = False
        toolchain.project_options["vapi"] = False
        toolchain.project_options["gtk_doc"] = False
        toolchain.project_options["man"] = False
        toolchain.project_options["bash_completion"] = False
        # enable the upstream test suites; patch 0001 gates the daemon-side
        # suites behind -Ddaemon=true (test/ links internal daemon libraries
        # declared in src/meson.build and expects real TTY/udev devices at
        # runtime, tools/tests runs through a D-Bus session-bus wrapper), so a
        # library-only build configures and runs the offline suites only:
        # libmm-glib/tests (test-common-helpers + test-pco) and the offline
        # cases of libqcdm/tests (test-qcdm)
        toolchain.project_options["tests"] = True
        toolchain.project_options["examples"] = False
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
        # run the offline upstream test suites ("meson test -v"); the
        # daemon-side suites (test/, tools/tests) are not built at all with
        # -Ddaemon=false, so only the offline ones execute
        with self._test_environment().vars(self).apply():
            Meson(self).test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libmm-glib.so (Mm* API); headers land in include/ModemManager/ (the
        # shared ModemManager.h + enums/errors/version headers) and
        # include/libmm-glib/ (the client mm-*.h headers); pkg-config name:
        # mm-glib (the generated ModemManager.pc is headers-only)
        self.cpp_info.libs = ["mm-glib"]
        self.cpp_info.includedirs = ["include/ModemManager", "include/libmm-glib"]
        self.cpp_info.set_property("cmake_file_name", "ModemManager")
        self.cpp_info.set_property("cmake_target_name", "ModemManager::ModemManager")
        self.cpp_info.set_property("pkg_config_name", "mm-glib")
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers (patterns proven in the accountsservice/atk recipes) ────────

    def _test_environment(self):
        # the test binaries link the just-built libmm-glib.so and the conan
        # glib shared libraries; put every relevant lib dir (build folder +
        # dependencies) on LD_LIBRARY_PATH so "meson test" can execute them
        environment = Environment()
        environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, "libmm-glib")
        )
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        tmpdir = os.path.join(self.build_folder, "tmp")
        if os.path.isdir(tmpdir):
            environment.define_path("TMPDIR", tmpdir)
        return environment

    def _build_environment(self):
        # meson runs build-time tools (gdbus-codegen, xsltproc, msgfmt) that
        # need a writable TMPDIR on HMDFS and the dependency bin dirs on PATH
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _append_dependency_pkg_config_paths(self):
        # meson reads dependencies through the native file pkg_config_path, not
        # the environment; PkgConfigDeps only covers what it generated itself
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_tools(self):
        # Conan's MesonToolchain emits c/cpp in [binaries] but leaves the
        # archiver to meson's guess chain (llvm-ar-15/llvm-ar/ar/gar), which
        # does not exist on the OHOS toolchain — inject llvm-ar/llvm-ranlib
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _augment_glib_pkg_config(self):
        # The generated libmm-glib sources are produced by build-time tools
        # looked up through pkg-config variables which PkgConfigDeps does not
        # emit (accountsservice pattern):
        #  - gnome.gdbus_codegen reads gdbus_codegen from gio-2.0.pc
        #  - include/ModemManager-names.h is generated by xsltproc (found via
        #    find_program, PATH-based) — covered by _build_environment PATH
        gdbus_codegen = self._create_python_tool_wrapper("gdbus-codegen")
        variables = {
            "gio-2.0": [
                f"gdbus_codegen={gdbus_codegen}",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if inserted:
                addition = "\n" + "\n".join(inserted)
                name_index = content.find("\nName:")
                if name_index >= 0:
                    content = content[:name_index] + addition + content[name_index:]
                else:
                    content = "\n".join(inserted) + "\n" + content
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _create_dbus_pc_alias(self):
        # dbus/1.14.10 recipe has no pkg_config_name, so PkgConfigDeps emits
        # "dbus.pc", but the ModemManager top-level meson.build asks for
        # dependency('dbus-1') and reads the interfaces_dir /
        # system_bus_services_dir / sysconfdir variables. Alias it and add the
        # upstream dbus-1.pc variables meson needs (accountsservice pattern).
        generated = os.path.join(self.generators_folder, "dbus.pc")
        alias = os.path.join(self.generators_folder, "dbus-1.pc")
        if not os.path.isfile(generated):
            self.output.warning("dbus.pc not generated by PkgConfigDeps; skipping dbus-1.pc alias")
            return
        with open(generated, encoding="utf-8") as handle:
            content = handle.read()
        content = self._add_pc_variables(content, (
            "datadir=${prefix}/share",
            "sysconfdir=${prefix}/etc",
            "localstatedir=${prefix}/var",
            "libexecdir=${prefix}/libexec",
            "interfaces_dir=${datadir}/dbus-1/interfaces",
            "system_bus_services_dir=${datadir}/dbus-1/system-services",
        ))
        with open(alias, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    @staticmethod
    def _add_pc_variables(content, variables):
        missing = [v for v in variables if v.split("=", 1)[0] + "=" not in content]
        if not missing:
            return content
        addition = "\n" + "\n".join(missing)
        name_index = content.find("\nName:")
        if name_index >= 0:
            return content[:name_index] + addition + content[name_index:]
        return "\n".join(missing) + "\n" + content

    def _create_python_tool_wrapper(self, tool_name):
        # Wrap the conan-installed python tool so its __file__ points at bin/
        # and it can locate its codegen package under share/glib-2.0; meson
        # lookups via the .pc variable then resolve to a working executable.
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return f"${{bindir}}/{tool_name}"
        wrapper_path = os.path.join(self.generators_folder, f"{tool_name}-python")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{sys.executable}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_path.replace("\\", "/")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        # OHOS requires packaged ELF files to carry a code signature
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        import glob
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
