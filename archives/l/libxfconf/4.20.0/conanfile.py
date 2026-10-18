#!/usr/bin/env python3
"""Conan recipe for libxfconf 4.20.0 — Xfce configuration storage (GDBus backend).

Upstream tarball : https://archive.xfce.org/src/xfce/xfconf/4.20/xfconf-4.20.0.tar.bz2
Build system     : Autotools (the 4.20.0 release tarball ships a generated
                   `configure`; xfconf did not move to meson in 4.20)

What the recipe builds
----------------------
  lib/libxfconf-0.so.3.0.0        the configuration client library (pkg-config
                                  name `libxfconf-0`, API version 0)
  bin/xfconf-query                CLI
  lib/xfce4/xfconf/xfconfd        the per-session settings daemon (libexec)
  lib/gio/modules/libxfconf-gsettings-backend.so
  share/dbus-1/services/org.xfce.Xfconf.service  (D-Bus activation metadata)

OHOS adaptation notes (single source patch, host-side only)
-----------------------------------------------------------
- config.guess/config.sub: the shipped Autoconf helpers predate the `ohos` OS
  name, so configure dies with "OS `ohos' not recognized". patches/0001 adds the
  triplet recognition only (no compiler flag, no platform macro, no change to a
  compiled translation unit) — see notes.md for the full evidence chain.
- gio-unix-2.0: configure requires the `gio-unix-2.0` pkg-config module. GLib is
  a Conan package whose cpp_info exposes `gio-unix-2.0` only as a header
  subdirectory (include/gio-unix-2.0) and declares no matching component, so
  PkgConfigDeps cannot emit that .pc file; generate() writes one that points at
  the dependency's real include directory.
- NLS/introspection/vala/gtk-doc disabled: no gettext runtime tooling, no
  gobject-introspection and no vapigen in the artifact repository. i18n call
  sites fall back to the identity macro of glib/gi18n.h with --disable-nls.
- make check is NOT part of build(): the upstream suite (tests/ + xfconf/abicheck)
  needs a live D-Bus *session bus* plus a passwd entry for the sandbox UID, which
  the CI image does not provide. The suite is executed out-of-band (see
  notes.md "上游测试实测") and the packaged smoke coverage lives in test_package/.
- install rewrites the ELF files (libtool relink strips the linker's RUNPATH and
  therefore its .codesign section); package() re-signs every installed ELF,
  otherwise the OHOS loader refuses to load it.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# OHOS SDK tools shipped with the device image / CI worker (same absolute paths
# the sibling libxfce4util 4.20.1 recipe uses); shutil.which() is the fallback.
_OHOS_BIN_DIRS = ("/data/service/hnp/bin", "/data/service/hnp/ohos-sdk/bin")


def _find_ohos_tool(name):
    for bin_dir in _OHOS_BIN_DIRS:
        candidate = os.path.join(bin_dir, name)
        if os.path.isfile(candidate):
            return candidate
    return shutil.which(name)


class LibxfconfConan(ConanFile):
    name = "libxfconf"
    version = "4.20.0"
    description = (
        "Xfce configuration storage system: libxfconf-0 client library, "
        "xfconf-query CLI and the xfconfd settings daemon (GDBus backend)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.xfce.org/xfce/xfconf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: gobject-2.0 / gio-2.0 / gio-unix-2.0 / gthread-2.0 >= 2.72.0
        #               libxfce4util-1.0 >= 4.17.3
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # libxfce4util 4.20.0 is not published in the artifact repository, 4.20.1
        # is the maintained ABI-compatible release for the same 4.20 series
        # (upstream最低要求 4.17.3，4.20.1 满足)。
        self.requires("libxfce4util/4.20.1", transitive_headers=True, transitive_libs=True)

    # ---------------------------------------------------------------- helpers
    def _glib_package_folder(self):
        glib = self.dependencies.host.get("glib") if self.dependencies else None
        if glib is None:
            return None
        return glib.package_folder

    def _write_gio_unix_pc(self):
        """Emit the `gio-unix-2.0` module that configure requires.

        Conan's glib recipe exposes gio-unix-2.0 purely as a header directory
        (include/gio-unix-2.0) and declares no `gio-unix` component, so
        PkgConfigDeps has nothing to turn into gio-unix-2.0.pc. configure.ac
        calls XDT_CHECK_PACKAGE([GIO_UNIX], [gio-unix-2.0], ...), hence the file
        is materialised here against the dependency's real include directory.
        """
        glib_folder = self._glib_package_folder()
        if not glib_folder:
            raise ConanException(
                "libxfconf: glib dependency package_folder is missing; "
                "cannot synthesise gio-unix-2.0.pc"
            )
        include_dir = os.path.join(glib_folder, "include", "gio-unix-2.0")
        if not os.path.isdir(include_dir):
            raise ConanException(
                f"libxfconf: expected gio-unix headers at {include_dir}"
            )
        pc_path = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(pc_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "prefix={prefix}\n"
                "includedir=${{prefix}}/include\n"
                "\n"
                "Name: GIO unix specific APIs\n"
                "Description: unix specific headers for glib I/O system\n"
                "Version: 2.84.0\n"
                "Requires: gio-2.0\n"
                "Cflags: -I${{includedir}}/gio-unix-2.0\n".format(prefix=glib_folder)
            )
        self.output.info(f"libxfconf: wrote {pc_path}")

    def _dependency_bin(self):
        """bin/ directory of the glib package (host tools used at build time)."""
        glib_folder = self._glib_package_folder()
        if not glib_folder:
            return None
        bin_dir = os.path.join(glib_folder, "bin")
        return bin_dir if os.path.isdir(bin_dir) else None

    def _tmp_dir(self):
        # OHOS /tmp is a read-only mount; keep autotools/glib scratch inside the
        # build folder (accountsservice/libxfce4util precedent).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_gio_unix_pc()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                # glib/gi18n.h degrades to the identity macro; avoids pulling the
                # stub sysroot libintl.h (same choice as 200+ archives recipes).
                "--disable-nls",
                # no gobject-introspection / vapigen artifact in the repository
                "--disable-introspection",
                "--disable-vala",
                # gtk-doc would need gtkdocize + a doc toolchain
                "--disable-gtk-doc",
            ]
        )
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])

        # configure.ac: XDT_CHECK_PACKAGE_BINARY([GDBUS_CODEGEN], [gio-2.0],
        #                                        [gdbus_codegen], [gdbus-codegen])
        # The gdbus-codegen that ships with the device image is a symlink into an
        # ancient glib 2.38.2 tree whose shebang is `#!/usr/bin/python3` (that
        # interpreter does not exist here), so AC_PATH_PROG cannot use it.  Pin
        # the build tool to the version-matched script inside the glib Conan
        # package, and put that bin/ first on the build PATH as well.
        dep_bin = self._dependency_bin()
        if dep_bin:
            codegen = os.path.join(dep_bin, "gdbus-codegen")
            if os.path.isfile(codegen):
                tc.configure_args.append(f"GDBUS_CODEGEN={codegen}")
                self.buildenv_info.prepend_path("PATH", dep_bin)
            else:
                self.output.warning(
                    f"libxfconf: {codegen} not found, relying on PATH lookup"
                )
        tc.generate()

        # OHOS /tmp is a read-only mount: point every scratch lookup at the build
        # folder for the whole conanbuild environment (configure probes, make,
        # install and the glib/gio runtime helpers all honour TMPDIR).
        tmpdir = self._tmp_dir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            self.buildenv_info.define_path(var, tmpdir)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    # ------------------------------------------------------------ ELF signing
    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = _find_ohos_tool("llvm-objcopy")
        signer = _find_ohos_tool("binary-sign-tool")
        for tool in (objcopy, signer):
            if not tool or not os.path.isfile(tool):
                raise ConanException(
                    f"libxfconf: required OHOS signing tool not found (llvm-objcopy/binary-sign-tool)"
                )
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets.extend(
                glob.glob(
                    os.path.join(self.package_folder, "lib", "**", pattern), recursive=True
                )
            )
        for subdir in ("bin", "sbin", "libexec"):
            binary_dir = os.path.join(self.package_folder, subdir)
            if not os.path.isdir(binary_dir):
                continue
            for root, _dirs, names in os.walk(binary_dir):
                for name in names:
                    path = os.path.join(root, name)
                    if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                        targets.append(path)
        signed = 0
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
            signed += 1
        self.output.info(f"libxfconf: re-signed {signed} installed ELF(s)")

    def package_info(self):
        # xfconf/libxfconf-0.pc.in: Name: xfconf, Libs -lxfconf-0,
        # Cflags -I${includedir}/xfce4/xfconf-0
        self.cpp_info.set_property("pkg_config_name", "libxfconf-0")
        self.cpp_info.libs = ["xfconf-0"]
        self.cpp_info.includedirs = ["include/xfce4/xfconf-0"]
        # The package installs a real CLI (bin/xfconf-query); declaring bindirs
        # explicitly keeps the R38/L0k CLI detection in sync with
        # archives/l/libxfconf/commands.json.
        self.cpp_info.bindirs = ["bin"]
        # Public headers only pull in GLib/GObject/GIO (xfconf.h -> glib.h,
        # xfconf-channel.h -> gio); libxfce4util is linked by libxfconf-0.so
        # itself, so it is declared for the runtime link closure.
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "glib::gthread-2.0",
            "libxfce4util::libxfce4util",
        ]
