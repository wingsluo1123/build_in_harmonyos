#!/usr/bin/env python3
"""Conan recipe — libfprint 1.94.10 (Meson).

Generic C API for fingerprint reader access (produces libfprint-2.so.2.0.0,
headers under include/libfprint-2/, pkg-config file libfprint-2.pc).

Adapted to HarmonyOS PC (aarch64):
- Upstream is a meson + ninja build; the autotools template was replaced by
  a real meson recipe (MesonToolchain + PkgConfigDeps), following the glib /
  gusb / accountsservice recipes in this repo.
- drivers=all keeps every upstream driver (aes3500/aes4000 need pixman-1 via
  the aes3k helper, uru4000 needs OpenSSL >= 3.0, elanspi needs gudev-1.0).
- introspection / doc / examples / installed-tests / metainfo / udev_rules /
  udev_hwdb are disabled: they need host-executable tools (fprint-list-metainfo
  is a cross-compiled binary that cannot run on the build host) or a udev
  environment absent from the OHOS sandbox. Patches 0001-0003 add the
  `examples` / `metainfo` meson_options switches and gate the subdir /
  custom_target so `-Dexamples=false -Dmetainfo=false` is accepted.
- R49: all dependency .pc files carry absolute per-package prefixes resolved
  under the conan package folders (no shared /usr/local injection); the
  gio-unix-2.0.pc shim is synthesised from the glib package folder.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibfprintConan(ConanFile):
    name = "libfprint"
    version = "1.94.10"
    description = "Generic C API for fingerprint reader access"
    license = "LGPL-2.1-or-later"
    homepage = "https://fprint.freedesktop.org/"
    url = ""
    package_type = "library"

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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # glib 2.84.0.1 pinned (gusb/0.4.9 was built against this ABI)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gusb/0.4.9")
        # json-glib/1.10.6 binary package on the ohpcd remote is corrupted:
        # its .so was rewritten by meson install (E999 root cause: absolute
        # paths in .dynstr replaced, lld codesign digest no longer matches),
        # so the OHOS loader refuses it (dlopen: Permission denied) and every
        # consumer's test_package fails at runtime with
        # "json_object_has_member: symbol not found" via gusb->json-glib.
        # json-glib/1.10.6.1 is the re-published fixed build (dlopen OK) ->
        # override gusb's transitive 1.10.6 pin to it (same package_id, ABI
        # compatible; verified: remote 1.10.6 .so sha b6fcccb9... fails to
        # load, remote 1.10.6.1 sha 2a5bb955... loads). See
        # DRAFT-libfprint-1.94.10-json-glib-dep-codesign-symbol-not-found.
        self.requires("json-glib/1.10.6.1", override=True)
        # Private build-time deps (not part of the public libfprint ABI):
        # gudev-1.0 (elanspi helper), pixman-1 (aes3k helper), openssl
        # (uru4000 helper), nss (declared per QA review). Marked
        # visible=False: used for compile/link of this package, not propagated
        # to consumers (Conan 2 requires every visible direct dependency to
        # appear in cpp_info.requires otherwise; accountsservice pattern).
        # libgudev (gudev-1.0) IS part of the propagated dependency closure
        # (referenced in cpp_info.requires below), so it must stay visible.
        self.requires("libgudev/238")
        self.requires("nss/3.118.1", visible=False)
        # NOTE: libusb/1.0.27 is deliberately NOT declared directly: gusb/0.4.9
        # (visible) already requires it transitively, so it is present in the
        # graph and PkgConfigDeps emits libusb-1.0.pc; a direct declaration
        # would make Conan complain "direct dependency 'libusb' is not used by
        # cpp_info.requires" (it is dual-visible via gusb, so visible=False
        # does not silence the check). fpi-usb-transfer.c gets libusb headers
        # through the propagated gusb dependency.
        # pixman-1 for the aes3k (aes3500/aes4000) driver helper
        self.requires("pixman/0.46.4.3", visible=False)
        # NOTE: libxmlb/0.3.19 (registry) requires glib/2.88.3 and would
        # conflict with the gusb-pinned glib/2.84.0.1 ("Version conflict in
        # the graph", G2 conan create). libxmlb is NOT needed by libfprint
        # nor by gusb/0.4.9 as built here (exploratory reqs/ had no xmlb.pc;
        # gusb.pc Requires only glib-2.0-unofficial/libusb-1.0/json-glib-1.0)
        # -> intentionally not declared. See notes.md.
        # uru4000 driver helper needs OpenSSL >= 3.0 (proved in the
        # exploratory build: dependency('openssl') -> 3.5.6.1.1)
        self.requires("openssl/3.5.6.1.1", visible=False)

    def build_requirements(self):
        # NOTE: QA requested meson/1.11.0.1, but that version's artifact is
        # broken on the ohpcd remote (conan download/install: "system
        # acceleration policy not enabled" / "Unable to find ... in remotes",
        # R41 evidence). meson/1.11.0 is downloadable and already cached, so
        # it is used instead — meson is a python tool, 1.11.0.x differs only
        # in patch level. See notes.md.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_gio_unix_pc()
        self._augment_glib_pkg_config()
        self._rewrite_dependency_pc_prefixes()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["drivers"] = "all"
        tc.project_options["introspection"] = False
        tc.project_options["udev_rules"] = "disabled"
        tc.project_options["udev_hwdb"] = "disabled"
        tc.project_options["gtk-examples"] = False
        tc.project_options["doc"] = False
        tc.project_options["examples"] = False
        tc.project_options["installed-tests"] = False
        tc.project_options["metainfo"] = False
        tc.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # OHOS-adapted meson install rewrites absolute build paths inside
        # installed .so .dynstr to 'X', which invalidates the lld-generated
        # .codesign digest. The OHOS loader verifies this digest at load time
        # and refuses the file (dlopen -> "Permission denied"), so the
        # test_package consumer cannot load libfprint-2.so.2. Restore the
        # pristine link-time .so from the meson build tree after install.
        self._restore_pristine_shared_libraries()
        self._sign_shared_libraries()

    def _restore_pristine_shared_libraries(self):
        """Replace meson-install-scrubbed .so copies with the pristine
        link-time files from the build tree (see package() rationale)."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir) or not os.path.isdir(self.build_folder):
            return
        for name in os.listdir(libdir):
            if ".so" not in name:
                continue
            target = os.path.join(libdir, name)
            if os.path.islink(target):
                continue
            source = None
            for root, _, files in os.walk(self.build_folder):
                if ".p" in root.replace("\\", "/").split("/"):
                    continue
                if name in files:
                    candidate = os.path.join(root, name)
                    if os.path.isfile(candidate):
                        source = candidate
                        break
            if source and os.path.abspath(source) != os.path.abspath(target):
                shutil.copy2(source, target)
                self.output.info(f"Restored pristine {name} from build tree")

    def _write_gio_unix_pc(self):
        """glib recipe does not export gio-unix-2.0.pc while libfprint's
        meson.build requires dependency('gio-unix-2.0'). Synthesise it from
        the glib package folder (ayatana-indicator-power pattern)."""
        glib = self.dependencies["glib"]
        prefix = glib.package_folder
        version = glib.ref.version
        content = (
            f"prefix={prefix}\n"
            f"libdir=${{prefix}}/lib\n"
            f"includedir=${{prefix}}/include\n"
            f"includedir1=${{prefix}}/include/gio-unix-2.0\n"
            "\n"
            "Name: GIO unix specific APIs\n"
            "Description: unix specific headers for glib I/O library\n"
            f"Version: {version}\n"
            "Requires: gobject-2.0 gio-2.0\n"
            f'Libs: -L"${{libdir}}"\n'
            f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"\n'
        )
        with open(os.path.join(self.generators_folder, "gio-unix-2.0.pc"), "w",
                  encoding="utf-8") as handle:
            handle.write(content)

    def _create_python_tool_wrapper(self, tool_name):
        """gnome.mkenums_simple needs glib-mkenums; PkgConfigDeps does not emit
        the glib_mkenums pkg-config variable. Wrap the conan-installed script
        (accountsservice/polkit pattern) so it runs under the build python."""
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

    def _augment_glib_pkg_config(self):
        """Add the glib_mkenums/glib_genmarshal pkg-config variables that
        PkgConfigDeps omits but gnome.mkenums_simple needs."""
        glib_mkenums = self._create_python_tool_wrapper("glib-mkenums")
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        variables = {
            "glib-2.0": [
                f"glib_mkenums={glib_mkenums}",
                f"glib_genmarshal={glib_genmarshal}",
            ],
            "gobject-2.0": [
                f"glib_mkenums={glib_mkenums}",
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

    def _rewrite_dependency_pc_prefixes(self):
        """R49 (fixpc.py pattern): every dependency .pc file in the generators
        folder must carry an absolute, non-system prefix. PkgConfigDeps already
        emits prefix=<package_folder>; defensively rewrite any bare '/', empty
        or relative prefix to the owning dependency's package folder (matched
        by .pc basename against each host dependency's installed .pc files)."""
        pc_dir = self.generators_folder
        if not os.path.isdir(pc_dir):
            return
        owner = {}
        for dep in self.dependencies.host.values():
            for rel in ("lib/pkgconfig", "share/pkgconfig", "lib64/pkgconfig"):
                base = os.path.join(dep.package_folder, rel)
                if not os.path.isdir(base):
                    continue
                for name in os.listdir(base):
                    if name.endswith(".pc"):
                        owner.setdefault(name, dep.package_folder)
        for name in os.listdir(pc_dir):
            if not name.endswith(".pc"):
                continue
            path = os.path.join(pc_dir, name)
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            prefix_line = next(
                (line for line in content.splitlines() if line.startswith("prefix=")),
                None)
            if prefix_line:
                value = prefix_line[len("prefix="):].strip()
                if os.path.isabs(value) and os.path.isdir(value):
                    continue
            target = owner.get(name)
            if not target:
                continue
            if prefix_line:
                content = content.replace(prefix_line, f"prefix={target}", 1)
            else:
                content = f"prefix={target}\n" + content
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _inject_meson_tools(self):
        """Inject ar/ranlib/pkg-config into the meson native/cross files so
        meson's compiler/archiver probes find the OHOS toolchain binaries."""
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={},
                                      check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/bin"):
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
                content = content.replace("[binaries]\n",
                                          "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _append_dependency_pkg_config_paths(self):
        """Make sure pkg-config resolves both the generators folder (PkgConfigDeps
        .pc files) and each host dependency's installed pkgconfig dirs (R49 —
        private per-build search path, never a shared system prefix)."""
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

    def _sign_shared_libraries(self):
        """NO-OP (kept for documentation only).

        Do NOT re-sign the packaged .so with binary-sign-tool here. The OHOS
        loader verifies the .codesign digest against the CURRENT file content:
        binary-sign-tool -selfSign replaces the pristine lld-generated
        .codesign (added automatically by -Wl,--code-sign) with a self-signed
        one that this sandbox loader rejects (dlopen -> "Permission denied"),
        so test_package consumers cannot load libfprint-2.so.2 at runtime.
        glib/gusb recipes keep the lld .codesign and load fine. CI applies its
        own signature at release time via ci/artifacts/sign.sh.
        """
        return
        # pylint: disable=unreachable
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run([signer, "sign", "-inFile", path,
                                "-outFile", signed, "-selfSign", "1"], check=True)
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libfprint")
        self.cpp_info.set_property("cmake_target_name", "libfprint::libfprint")
        self.cpp_info.set_property("pkg_config_name", "libfprint-2")
        # Base library name WITHOUT the "lib" prefix: CMakeDeps emits
        # find_library(NAMES fprint-2) which on Linux searches lib/libfprint-2.so.
        # Using "libfprint-2" here would make CMake look for liblibfprint-2.so
        # (find_library prepends "lib") -> "Library 'libfprint-2' not found".
        # -lfprint-2 matches the installed libfprint-2.so.2.0.0 and the
        # pkg-config Libs line, so pkg-config consumers stay consistent too.
        self.cpp_info.libs = ["fprint-2"]
        self.cpp_info.includedirs = ["include/libfprint-2"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "gusb::gusb",
            "libgudev::gudev-1.0",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
