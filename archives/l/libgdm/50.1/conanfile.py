#!/usr/bin/env python3
"""Conan recipe — libgdm 50.1 (meson).

GDM Display Manager client library (libgdm) for HarmonyOS PC (aarch64-ohos).
Built with meson against conan glib/gio/json-glib/polkit/systemd/... .

libgdm.so is `library('gdm')` in libgdm/meson.build; the whole gdm tree
(daemon, utils, pam_gdm, data, po, tests, docs) is built because the top-level
meson.build has no option to skip subdirs — the daemon needs the same deps.

OHOS adaptations (patches/0001-0005):
  - meson_options.txt adds an `introspection` feature option (default disabled)
    so the GIR block in libgdm/meson.build can be compiled out (no
    gobject-introspection scanner needed on OHOS).
  - libgdm/meson.build: gnome.generate_gir wrapped in `if
    get_option('introspection').enabled()`.
  - daemon/meson.build: new source gdm-lckpwdf-compat.c.
  - daemon/gdm-lckpwdf-compat.c: OHOS musl libc.so does not export
    lckpwdf()/ulckpwdf() and the SDK sysroot ships an empty libcrypt.a;
    provide a flock(2)-based implementation so gdm-dynamic-user-store.c works.
  - docs/meson.build: build gnome.yelp help pages only when itstool is
    available (non-essential for the libgdm library).

Generated-side fixes (recipe generate(), no source patch):
  - gio-unix-2.0.pc is synthesized from gio-2.0.pc (glib recipe has no
    gio-unix component) so dependency('gio-unix-2.0') resolves.
  - libsystemd.pc synthesized from the systemd package (its recipe only emits
    systemd.pc; gdm needs the libsystemd name).
  - polkit-gobject-1.pc copied from the polkit package and the bare `prefix=/`
    rewritten to the real package folder (polkit/127 declares no cpp_info
    component, so PkgConfigDeps would not emit it).
  - cc.find_library('pam'): OHOS sysroot has no libpam; the linux-pam package
    lib dir is injected into the meson toolchain link args.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibgdmConan(ConanFile):
    name = "libgdm"
    version = "50.1"
    description = "GDM — GNOME Display Manager (client library libgdm)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gdm"
    url = ""  # CI fills this
    package_type = "library"

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

    def requirements(self):
        # libgdm.so links glib/gio/gio-unix + libsystemd (logind provider);
        # headers are public API → transitive headers/libs.
        # accountsservice/json-glib/libgudev floor glib at 2.84.0.1 (this OHOS
        # conan fork cannot mix exact glib versions); match 2.84.0.1 and keep it
        # visible + transitive so consumers see glib/gobject/gio headers/libs.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("systemd/261.1", transitive_headers=True, transitive_libs=True)
        # systemd/261.1 requires zlib/1.3.1 while glib (2.84.0.x) requires
        # zlib/1.3.1.1 → force the higher revision (abiword pattern).
        self.requires("zlib/1.3.1.1", override=True)
        # ── daemon-side deps: needed by the gdm daemon executables only, not by
        # the libgdm library → visible=False keeps the consumer cpp_info clean.
        self.requires("json-glib/1.10.6.1", visible=False)
        self.requires("accountsservice/26.27.3", visible=False)
        self.requires("polkit/127", visible=False)
        self.requires("libaudit/2.7.4", visible=False)
        self.requires("libgudev/238", visible=False)
        self.requires("linux-pam/1.7.2", visible=False)
        self.requires("check/0.15.2", visible=False)   # upstream m-common test
        self.requires("dconf/0.40.0.1", visible=False) # data/dconf custom_target binary

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def _build_environment(self):
        """PATH/LD_LIBRARY_PATH/TMPDIR for the OHOS build+test+install steps.

        glib's bin/ provides gdbus-codegen, glib-mkenums, glib-compile-schemas;
        dconf's bin/ provides the dconf tool used by data/dconf custom_target;
        every dep lib dir goes on LD_LIBRARY_PATH so freshly linked OHOS
        binaries (m-common test, dconf compile) can load their deps.
        """
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

    def _stage_glib_elf_tools(self):
        """OHOS refuses to exec the glib package's C tools (glib-compile-schemas
        & co) because their link-time .codesign is not valid on this worker
        ("Operation not permitted"). Copy the ELF tools into a per-build folder
        and re-sign them with binary-sign-tool; point the pkg-config *_tool
        variables at these staged copies. Python tools (gdbus-codegen,
        glib-mkenums, glib-genmarshal) run fine from the package and stay put.
        """
        glib = next((d for d in self.dependencies.host.values()
                     if getattr(d.ref, "name", "") == "glib"), None)
        if not glib:
            return {}
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        staged = {}
        elf_tools = [
            "glib-compile-schemas",
            "glib-compile-resources",
            "gio-querymodules",
            "gobject-query",
        ]
        for tool in elf_tools:
            src = os.path.join(glib.package_folder, "bin", tool)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(tools_dir, tool)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
            signer = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(signer):
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                         .format(sg=signer, f=dst), env=None, quiet=True, ignore_errors=True)
            staged[tool] = dst
        return staged

    def _augment_glib_pkg_config(self):
        """meson's gnome module reads *_tool pkg-config variables from the
        glib/gio pc files (glib_compile_schemas from gio-2.0.pc, glib_mkenums
        from glib-2.0.pc, gdbus_codegen from gio-2.0.pc ...). PkgConfigDeps does
        not emit them; add them (the generated .pc already defines
        bindir=${prefix}/bin). Without this, meson configure fails with "Could
        not get pkg-config variable and no default provided"."""
        staged = self._stage_glib_elf_tools()
        variables = {
            "glib-2.0": [
                "glib_mkenums=${bindir}/glib-mkenums",
                "glib_genmarshal=${bindir}/glib-genmarshal",
                "gobject_query=" + staged["gobject-query"] if "gobject-query" in staged else "gobject_query=${bindir}/gobject-query",
            ],
            "gobject-2.0": [
                "glib_mkenums=${bindir}/glib-mkenums",
            ],
            "gio-2.0": [
                "gdbus_codegen=${bindir}/gdbus-codegen",
                "glib_compile_schemas=" + staged["glib-compile-schemas"] if "glib-compile-schemas" in staged else "glib_compile_schemas=${bindir}/glib-compile-schemas",
                "glib_compile_resources=" + staged["glib-compile-resources"] if "glib-compile-resources" in staged else "glib_compile_resources=${bindir}/glib-compile-resources",
                "gio_querymodules=" + staged["gio-querymodules"] if "gio-querymodules" in staged else "gio_querymodules=${bindir}/gio-querymodules",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content_pc = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content_pc:
                    inserted.append(entry)
            if inserted:
                addition_lines = "\n" + "\n".join(inserted)
                name_index = content_pc.find("\nName:")
                if name_index >= 0:
                    content_pc = content_pc[:name_index] + addition_lines + content_pc[name_index:]
                else:
                    content_pc = "\n".join(inserted) + "\n" + content_pc
            # gi18n.h maps gettext()/textdomain() to g_libintl_* (glib's
            # shared proxy-libintl); without -lintl the gdm executables keep
            # undefined g_libintl_gettext/g_libintl_textdomain at link time.
            libs_line = next((line for line in content_pc.splitlines()
                              if line.startswith("Libs:")), None)
            if libs_line is not None and "-lintl" not in libs_line.split():
                content_pc = content_pc.replace(
                    libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content_pc)

    def _write_gio_unix_pc(self):
        """meson needs dependency('gio-unix-2.0'); glib recipe has no such
        component. gio-unix-2.0.pc is just gio-2.0.pc renamed."""
        src = os.path.join(self.generators_folder, "gio-2.0.pc")
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        if not os.path.isfile(src) or os.path.isfile(dst):
            return
        with open(src, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("Name: gio-2.0", "Name: gio-unix-2.0")
        with open(dst, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _write_libsystemd_pc(self):
        """gdm does dependency('libsystemd'); systemd recipe only emits
        systemd.pc, so synthesize libsystemd.pc from the package folder."""
        systemd = next((d for d in self.dependencies.host.values()
                        if getattr(d.ref, "name", "") == "systemd"), None)
        if not systemd:
            return
        dst = os.path.join(self.generators_folder, "libsystemd.pc")
        if os.path.isfile(dst):
            return
        prefix = systemd.package_folder.replace("\\", "/")
        version = getattr(systemd.ref, "version", "261")
        content = (
            f"prefix={prefix}\n"
            f"libdir={prefix}/lib\n"
            f"includedir={prefix}/include\n"
            "\n"
            "Name: libsystemd\n"
            "Description: systemd Library\n"
            f"Version: {version}\n"
            "Libs: -L${libdir} -lsystemd\n"
            "Cflags: -I${includedir}\n"
        )
        with open(dst, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _augment_polkit_pc(self):
        """gdm hard-requires polkit-gobject-1 at configure. polkit/127 declares
        no cpp_info component → PkgConfigDeps only emits polkit.pc. Copy the
        real polkit-gobject-1.pc from the polkit package and rewrite the bare
        `prefix=/` (built with --prefix=/ + DESTDIR) to the package folder."""
        pc = os.path.join(self.generators_folder, "polkit-gobject-1.pc")
        if os.path.isfile(pc):
            return
        polkit = next((d for d in self.dependencies.host.values()
                       if getattr(d.ref, "name", "") == "polkit"), None)
        if not polkit:
            return
        source = None
        prefix = polkit.package_folder.replace("\\", "/")
        for relative in ("lib/pkgconfig/polkit-gobject-1.pc",
                         "share/pkgconfig/polkit-gobject-1.pc"):
            candidate = os.path.join(polkit.package_folder, relative)
            if os.path.isfile(candidate):
                source = candidate
                break
        if not source:
            self.output.warning("polkit-gobject-1.pc not found in polkit package; skipping")
            return
        with open(source, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        content = "\n".join(
            "prefix=" + prefix if line.startswith("prefix=") else line
            for line in content.splitlines()
        )
        for var in ("datadir=${prefix}/share",
                    "policydir=${datadir}/polkit-1/actions"):
            key = var.split("=", 1)[0] + "="
            if key not in content:
                content = var + "\n" + content
        with open(pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _inject_ar_ranlib(self):
        # MesonToolchain omits ar/ranlib; meson then cannot find llvm-ar.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            for name in ("llvm-ar", "ar"):
                cand = os.path.join(bindir, name)
                if os.path.isfile(cand):
                    ar = cand
                    break
            for name in ("llvm-ranlib", "ranlib"):
                rlc = os.path.join(bindir, name)
                if os.path.isfile(rlc):
                    ranlib = rlc
                    break
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _inject_pkg_config(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if pkg_config and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if ("\npkg-config =" not in content
                    and "\npkgconfig =" not in content
                    and "[binaries]" in content):
                content = content.replace(
                    "[binaries]\n", "[binaries]\npkg-config = '{}'\n".format(pkg_config), 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._write_gio_unix_pc()
        self._write_libsystemd_pc()
        self._augment_polkit_pc()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["plymouth"] = "disabled"
        tc.project_options["selinux"] = "disabled"
        tc.project_options["systemd-journal"] = False
        tc.project_options["systemdsystemunitdir"] = "no"
        tc.project_options["systemduserunitdir"] = "no"
        tc.project_options["x11-support"] = False
        tc.project_options["libaudit"] = "enabled"
        tc.project_options["logind-provider"] = "systemd"
        # cc.find_library('pam'): OHOS sysroot has no libpam; expose the
        # linux-pam package dirs to the meson toolchain.
        pam = next((d for d in self.dependencies.host.values()
                    if getattr(d.ref, "name", "") == "linux-pam"), None)
        if pam:
            pam_lib = os.path.join(pam.package_folder, "lib")
            pam_inc = os.path.join(pam.package_folder, "include")
            if os.path.isdir(pam_lib):
                tc.c_link_args.append("-L{}".format(pam_lib))
            if os.path.isdir(pam_inc):
                tc.c_args.append("-I{}".format(pam_inc))
        tc.generate()
        self._inject_ar_ranlib()
        self._inject_pkg_config()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self):
                meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._sign_elf_files()

    def _sign_elf_files(self):
        """Re-sign ELF files after meson install (RPATH rewrite invalidates the
        link-time .codesign). Best-effort: skip when tools are absent."""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        if not os.path.isfile(objcopy):
            objcopy = shutil.which("llvm-objcopy") or ""
        targets = []
        for top in ("bin", "lib", "sbin", "libexec"):
            base = os.path.join(self.package_folder, top)
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    path = os.path.join(root, fname)
                    if os.path.islink(path):
                        continue
                    try:
                        if open(path, "rb").read(4) != b"\x7fELF":
                            continue
                    except Exception:
                        continue
                    targets.append(path)
        for path in targets:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=path),
                         env=None, quiet=True, ignore_errors=True)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=path),
                     env=None)

    def package_info(self):
        # library('gdm') → libgdm.so, pkg-config filebase 'gdm' → gdm.pc
        self.cpp_info.libs = ["gdm"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "gdm")
        self.cpp_info.set_property("cmake_target_name", "gdm::gdm")
        self.cpp_info.set_property("pkg_config_name", "gdm")
        # libgdm.so links glib/gio and libsystemd; headers pull in gio/gio.h.
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "systemd::systemd",
        ]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
