#!/usr/bin/env python3
"""Conan recipe — gupnp-dlna 0.12.0 (Meson).

GUPnP DLNA provides DLNA profile definitions and a metadata-based profile
guesser. Two libraries are built: the core `gupnp-dlna-2.0` library and the
GStreamer metadata backend (`gupnp-dlna-gst-2.0`), plus the loadable backend
module (`libgstreamer.so`) that libgupnp-dlna opens at runtime through
GModule. Upstream also installs two command line tools:
`gupnp-dlna-info-2.0` and `gupnp-dlna-ls-profiles-2.0`.

The package is built as a shared library on HarmonyOS PC so that consumers
share one ELF load scope and the metadata backend module keeps its upstream
shared-module shape. glib2/gstreamer/gst-plugins-base are static packages:
their archives are embedded into our shared objects, and ELF interposition
makes the first-loaded definition win for UND references. The backend module
and libgupnp-dlna-gst-2.0.so nevertheless each carry their own defined
static-glib state, so loading the module hits the GType registry split
(device probe: SIGABRT); recorded as a platform limitation in notes.md.

Compile-time DATA_DIR is the configure-time prefix ("/"), so the DLNA profile
directory and the metadata backend directory are exported through runenv_info
(GUPNP_DLNA_PROFILE_DIR / GUPNP_DLNA_METADATA_BACKEND_DIR), matching the
gupnp-av 0.14.5 GUPNP_AV_DATADIR precedent.
"""
import glob
import os
import pathlib
import platform
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GupnpDlnaConan(ConanFile):
    name = "gupnp-dlna"
    version = "0.12.0"
    description = "DLNA profiles and metadata-based profile guesser for GUPnP"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gupnp-dlna"
    url = "https://gitlab.gnome.org/GNOME/gupnp-dlna"
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
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("gstreamer/1.28.3", transitive_headers=True, transitive_libs=True)
        self.requires("gst-plugins-base/1.28.3", transitive_headers=True, transitive_libs=True)
        # PIC static zlib: glib2 links zlib into our shared objects; the plain
        # zlib/1.3.1 archives are non-PIC and fail with R_AARCH64 relocation
        # errors (same override as gst-plugins-bad / gst-libav recipes).
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------

    def generate(self):
        PkgConfigDeps(self).generate()
        gen_dir = pathlib.Path(self.generators_folder)
        # PkgConfigDeps only emits glib-2.0.pc (glib2) and plain
        # gstreamer.pc/gst-plugins-base.pc; gupnp-dlna's meson.build asks for
        # gobject-2.0/gio-2.0/gmodule-2.0, gstreamer-1.0 and
        # gstreamer-pbutils-1.0. Write the sub-package .pc wrappers.
        self._create_glib_subpkg_pcs(gen_dir)
        self._create_gstreamer_pcs(gen_dir)

        tc = MesonToolchain(self)
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # introspection pulls g-ir-scanner (unavailable on the build host);
        # vapi depends on introspection; gtk_doc is not built.
        tc.project_options["introspection"] = False
        tc.project_options["vapi"] = False
        tc.project_options["gtk_doc"] = False
        tc.project_options["gstreamer_backend"] = "enabled"
        tc.project_options["default_backend"] = "gstreamer"
        tc.c_link_args.extend(self._glib_libintl_link_args())
        tc.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()
        # CI worker lld dynamically links libxml2.so.16 from the SDK's
        # llvm/lib; prepend it for the configure-time compiler probes
        # (E120/E132, same handling as gupnp-av 0.14.5).
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            self.output.info(
                "gupnp-dlna: prepend SDK llvm/lib to LD_LIBRARY_PATH: %s" % sdk_llvm_lib)

    def _create_glib_subpkg_pcs(self, gen_dir):
        """Wrapper .pc files for glib2 sub-packages (meson looks up
        glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0; conan only ships a flat
        glib2.pc). Static glib archives are embedded in our shared objects,
        so the Libs line lists the full glib library set."""
        prefix = self._dep_prefix("glib2")
        if not prefix:
            return
        libdir = "${prefix}/lib"
        inc = "${prefix}/include/glib-2.0"
        inc1 = "${prefix}/lib/glib-2.0/include"
        bindir = "${prefix}/bin"
        datadir = "${prefix}/share"

        (gen_dir / "glib-2.0.pc").write_text(
            f"prefix={prefix}\nlibdir={libdir}\nincludedir={inc}\nincludedir1={inc1}\n"
            f"bindir={bindir}\ndatadir={datadir}\n\n"
            f"glib_genmarshal=${{bindir}}/glib-genmarshal\n"
            f"gobject_query=${{bindir}}/gobject-query\n"
            f"glib_mkenums=${{bindir}}/glib-mkenums\n\n"
            f"Name: GLib\nDescription: C Utility Library\nVersion: 2.88.0\n"
            f'Libs: -L"${{libdir}}" -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt\n'
            f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"\n'
            f"Requires: pcre2 zlib\n"
        )
        subs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"]),
            "gio-2.0.pc": ("GIO", "gio-2.0", ["gobject-2.0"]),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"]),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"]),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"]),
        }
        for fn, (nm, lib, reqs) in subs.items():
            (gen_dir / fn).write_text(
                f"prefix={prefix}\nlibdir={libdir}\nincludedir={inc}\nincludedir1={inc1}\n"
                f"bindir={bindir}\ndatadir={datadir}\n\n"
                f"Name: {nm}\nDescription: GLib sub-package ({nm})\nVersion: 2.88.0\n"
                f"Requires: {', '.join(reqs)}\n"
                f'Libs: -L"${{libdir}}" -l{lib}\n'
                f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"\n'
            )

    def _create_gstreamer_pcs(self, gen_dir):
        """Wrapper .pc files for gstreamer/gst-plugins-base sub-packages.

        gupnp-dlna asks pkg-config for gstreamer-1.0 and
        gstreamer-pbutils-1.0 only. Both conan packages are static, so the
        pbutils wrapper carries the whole static gst link chain in Libs to
        keep meson's default -Wl,--no-undefined satisfied.
        """
        gst_prefix = self._dep_prefix("gstreamer")
        base_prefix = self._dep_prefix("gst-plugins-base")
        if not gst_prefix:
            return
        if not base_prefix:
            base_prefix = gst_prefix
        gst_libdir = "${gst_prefix}/lib"
        base_libdir = "${base_prefix}/lib"
        # gstreamer and gst-plugins-base both install headers under
        # include/gstreamer-1.0 in their own package folders; gstbase lives in
        # the gstreamer package while gstpbutils/gstaudio/gstvideo/gsttag live
        # in gst-plugins-base. Every wrapper must expose both.
        gst_inc = "${gst_prefix}/include/gstreamer-1.0"
        base_inc = "${base_prefix}/include/gstreamer-1.0"
        cflags = f'-I"${{gst_includedir}}" -I"${{base_includedir}}"'
        (gen_dir / "gstreamer-1.0.pc").write_text(
            f"gst_prefix={gst_prefix}\nbase_prefix={base_prefix}\n"
            f"libdir={gst_libdir}\n"
            f"gst_includedir={gst_inc}\nbase_includedir={base_inc}\n\n"
            f"Name: GStreamer\nDescription: GStreamer core library\nVersion: 1.28.3\n"
            f"Requires: glib-2.0, gobject-2.0, gmodule-no-export-2.0\n"
            f'Libs: -L"${{libdir}}" -lgstreamer-1.0 -lm -ldl -lpthread\n'
            f"Cflags: {cflags}\n"
        )
        base_pcs = {
            "gstreamer-base-1.0.pc": ("GStreamer Base", "gstbase-1.0", ["gstreamer-1.0"]),
            "gstreamer-audio-1.0.pc": ("GStreamer Audio", "gstaudio-1.0", ["gstreamer-1.0", "gstreamer-base-1.0"]),
            "gstreamer-video-1.0.pc": ("GStreamer Video", "gstvideo-1.0", ["gstreamer-1.0", "gstreamer-base-1.0"]),
            "gstreamer-tag-1.0.pc": ("GStreamer Tag", "gsttag-1.0", ["gstreamer-1.0", "gstreamer-base-1.0"]),
        }
        for fn, (nm, lib, reqs) in base_pcs.items():
            (gen_dir / fn).write_text(
                f"gst_prefix={gst_prefix}\nbase_prefix={base_prefix}\n"
                f"libdir={base_libdir}\ngstlibdir={gst_libdir}\n"
                f"gst_includedir={gst_inc}\nbase_includedir={base_inc}\n\n"
                f"Name: {nm}\nDescription: GStreamer sub-package ({nm})\nVersion: 1.28.3\n"
                f"Requires: {', '.join(reqs)}\n"
                f'Libs: -L"${{libdir}}" -L"${{gstlibdir}}" -l{lib}\n'
                f"Cflags: {cflags}\n"
            )
        (gen_dir / "gstreamer-pbutils-1.0.pc").write_text(
            f"gst_prefix={gst_prefix}\nbase_prefix={base_prefix}\n"
            f"libdir={base_libdir}\ngstlibdir={gst_libdir}\n"
            f"gst_includedir={gst_inc}\nbase_includedir={base_inc}\n\n"
            f"Name: GStreamer Plugins Base Utils\n"
            f"Description: GStreamer pbutils (discoverer) library\nVersion: 1.28.3\n"
            f"Requires: glib-2.0, gobject-2.0, gmodule-no-export-2.0, zlib, orc-0.4\n"
            f'Libs: -L"${{libdir}}" -L"${{gstlibdir}}" -lgstpbutils-1.0 -lgstaudio-1.0 '
            f"-lgstvideo-1.0 -lgsttag-1.0 -lgstbase-1.0 -lgstreamer-1.0 -lm -ldl -lpthread\n"
            f"Cflags: {cflags}\n"
        )

    def _dep_prefix(self, name):
        for dep in self.dependencies.values():
            if dep.ref.name == name and dep.package_folder:
                return str(dep.package_folder).replace("\\", "/")
        return None

    # ------------------------------------------------------------------
    # build/package
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # The loader resolves DT_NEEDED through libgupnp-dlna-2.0.so.4 /
            # libgupnp-dlna-gst-2.0.so.4, but meson publishes those names as
            # symlinks and OHOS refuses symlink(2). Materialize them as copies
            # before the tests run (the test-set binary links the shared core
            # library).
            self._ensure_library_aliases(self.build_folder)
            if not cross_building(self) and can_run(self):
                self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream meson tests.

        `test-sets` is a compiled GLib g_test binary. `discoverer` is a bash
        script (its shebang is `#!/bin/bash`) that needs the external
        gupnp-dlna-media collection and exits 77 (skip) when it is absent.
        OHOS has no /bin/bash and rejects execve of scripts (no
        binfmt_script); `meson test` prefixes the shebang interpreter, so a
        `--wrapper bash` would stack a second, nonexistent `/bin/bash`
        (device run: "/data/service/hnp/bin/bash: /bin/bash: No such file").
        Run the generated script explicitly with the device bash and the
        same environment meson would provide; upstream exit 77 counts as
        SKIP.
        """
        if self.settings.os != "OHOS":
            Meson(self).test()
            return
        prefix = ('meson test -v -C "{}" --timeout-multiplier=16 --no-rebuild '
                  .format(self.build_folder))
        self.run(prefix + "test-sets")
        bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        media_dir = os.path.join(self.source_folder, "tests", "gupnp-dlna-media")
        script = os.path.join(self.build_folder, "tests", "test-discoverer.sh")
        self.run(
            'MEDIA_DIR="{media}" FILE_LIST="{media}/media-list.txt" '
            'GUPNP_DLNA_PROFILE_DIR="{src}/data" '
            'GUPNP_DLNA_METADATA_BACKEND_DIR="{bld}/libgupnp-dlna/metadata-backends/gstreamer" '
            '"{bash}" "{script}"; rc=$?; '
            'if [ $rc -eq 77 ]; then '
            'echo "discoverer: SKIP (upstream exit 77: media set absent)"; '
            'exit 0; fi; exit $rc'.format(
                media=media_dir, src=self.source_folder,
                bld=self.build_folder, bash=bash, script=script))

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._restore_pristine_binaries()
        self._ensure_library_aliases(os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _ensure_library_aliases(self, root):
        """Recreate the SONAME and linker-name aliases as real copies.

        Meson links both libraries with `version: '4.0.0'` and publishes
        libX.so.4 / libX.so as symlinks to libX.so.4.0.0. The OHOS /storage
        sandbox denies symlink(2), so on the device only the fully versioned
        file exists: the loader cannot find the NEEDED `libX.so.4` name and
        consumers cannot link with `-lX` (atk 2.38.0.1.1 precedent). Recreate
        both aliases as byte-identical copies; on hosts where meson already
        created the links they exist and are left untouched.
        """
        if not os.path.isdir(root):
            return
        for libname in ("gupnp-dlna-2.0", "gupnp-dlna-gst-2.0"):
            prefix = "lib{}.so.".format(libname)
            candidates = []
            for path in glob.glob(os.path.join(root, "**", prefix + "*"),
                                  recursive=True):
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                version = os.path.basename(path)[len(prefix):]
                parts = version.split(".")
                # Skip meson's <file>.symbols intermediates and any already
                # materialized alias: only the full N.M.K file is a source.
                if len(parts) < 3 or not all(p.isdigit() for p in parts):
                    continue
                if self._is_elf(path):
                    candidates.append(path)
            if not candidates:
                continue
            source = max(candidates, key=os.path.getsize)
            base = os.path.basename(source)
            major = base[len(prefix):].split(".")[0]
            for alias in (prefix + major, prefix[:-1]):
                destination = os.path.join(os.path.dirname(source), alias)
                if os.path.lexists(destination):
                    continue
                try:
                    os.symlink(base, destination)
                except (OSError, NotImplementedError):
                    shutil.copy2(source, destination)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _restore_pristine_binaries(self):
        """meson install rewrites DT_RUNPATH of installed ELFs, which
        invalidates the OHOS per-file code signature embedded by lld; the
        loader then rejects them at load/dlopen time. Overwrite the installed
        copies with the pristine build-tree artifacts (gst-plugins-bad /
        E504 precedent). Includes the metadata backend module directory
        (lib/gupnp-dlna) and the CLI tools (bin)."""
        build_dir = self.build_folder
        index = {}
        for root, _, files in os.walk(build_dir):
            for f in files:
                p = os.path.join(root, f)
                if not os.path.islink(p) and os.path.isfile(p):
                    index.setdefault(f, p)
        restored = 0
        for sub in ("lib", os.path.join("lib", "gupnp-dlna"), "bin"):
            d = os.path.join(self.package_folder, sub)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                dst = os.path.join(d, f)
                if os.path.islink(dst) or not os.path.isfile(dst):
                    continue
                src = index.get(f)
                if src and os.path.getsize(src) == os.path.getsize(dst):
                    shutil.copy2(src, dst)
                    restored += 1
                elif src:
                    self.output.warning(
                        f"pristine artifact size mismatch for {f}: "
                        f"{src} vs {dst} -- install copy left in place")
                elif f.endswith(".so") or ".so." in f:
                    self.output.warning(
                        f"no build-tree counterpart found for {f} -- "
                        f"install copy left in place")
        self.output.info(
            f"Restored {restored} pristine build artifacts over meson "
            f"install output (rpath rewrite invalidates OHOS ELF signatures)")

    # ------------------------------------------------------------------
    # package_info
    # ------------------------------------------------------------------

    def package_info(self):
        # Two upstream libraries: the core guesser/profile engine and the
        # GStreamer utility library used by the metadata backend module.
        # Order matters for static linkers: the gst utils library depends on
        # the core library.
        self.cpp_info.libs = ["gupnp-dlna-gst-2.0", "gupnp-dlna-2.0"]
        self.cpp_info.includedirs = ["include/gupnp-dlna-2.0"]
        # Upstream installs gupnp-dlna-info-2.0 and gupnp-dlna-ls-profiles-2.0
        # to bin/ (PF8/R38 pairing with the software-level commands.json).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "glib2::glib2",
            "libxml2::libxml2",
            "gstreamer::gstreamer",
            "gst-plugins-base::gst-plugins-base",
        ]
        self.cpp_info.set_property("cmake_file_name", "gupnp-dlna-2.0")
        self.cpp_info.set_property("cmake_target_name", "gupnp-dlna-2.0::gupnp-dlna-2.0")
        self.cpp_info.set_property("pkg_config_name", "gupnp-dlna-2.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        # Compile-time DATA_DIR is the configure-time prefix ("/"): point the
        # profile loader and the GModule backend loader at the package copies.
        profiles = os.path.join(self.package_folder, "share",
                                "gupnp-dlna-2.0", "dlna-profiles")
        if os.path.isdir(profiles):
            self.runenv_info.define_path("GUPNP_DLNA_PROFILE_DIR", profiles)
        backend = os.path.join(self.package_folder, "lib", "gupnp-dlna")
        if os.path.isdir(backend):
            self.runenv_info.define_path("GUPNP_DLNA_METADATA_BACKEND_DIR", backend)
        # GStreamer discovers its plugins through GST_PLUGIN_PATH; the
        # gstreamer/gst-plugins-base conan packages ship them under
        # lib/gstreamer-1.0.
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                # Test requirements can surface here without a package
                # folder during package_info(); nothing to point at.
                continue
            plugins = os.path.join(dep.package_folder, "lib", "gstreamer-1.0")
            if os.path.isdir(plugins):
                self.runenv_info.prepend_path("GST_PLUGIN_PATH", plugins)
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))

    # ------------------------------------------------------------------
    # helpers (same family as gupnp-av 0.14.5 / atk 2.38.0.1.1)
    # ------------------------------------------------------------------

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # OHOS: meson's ninja detection runs `ninja` through python
        # subprocess; bare-name resolution is unreliable and the default
        # LD_LIBRARY_PATH can miss libc++_shared. Pass an absolute NINJA path
        # and prepend /system/lib64 (gupnp-av / glib 2.84.0 precedent).
        ninja = os.environ.get("NINJA") or shutil.which("ninja")
        if ninja and os.path.isfile(ninja):
            environment.define_path("NINJA", ninja)
        # On an empty env prepend_path yields exactly "/system/lib64", so a
        # single call covers both the inherited and the unset case.
        environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
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
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
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

    @staticmethod
    def _host_needs_clang_wrapper():
        """E120/E132 only reproduce on the x86_64 CI worker, where the SDK
        lld dynamically links libxml2.so.16 from llvm/lib. On the native
        aarch64 OHOS device the plain compiler links fine, and OHOS rejects
        exec of unsigned script files (no binfmt_script), so a wrapper
        script would fail with EACCES there."""
        return platform.machine().lower() not in ("aarch64", "arm64")

    def _make_clang_wrapper(self, cc):
        """Generate a clang wrapper that exports the SDK llvm/lib before
        exec'ing the real compiler. lld itself links against libxml2.so.16
        from that directory, and meson's compiler/linker probes run in
        subprocesses that the conan build env does not always reach
        (E120/E132, verified on CI workers; same as gupnp-av 0.14.5)."""
        if not cc or not os.path.isfile(cc):
            return None
        sdk_lib = self._sdk_llvm_libdir()
        if not sdk_lib:
            return None
        bindir = os.path.join(self.generators_folder, "clang-wrappers")
        os.makedirs(bindir, exist_ok=True)
        wrappers = {}
        for suffix in ("", "++"):
            wrapper = os.path.join(bindir, f"clang{suffix}")
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write(
                    "#!/data/service/hnp/bin/bash\n"
                    f'export LD_LIBRARY_PATH="{sdk_lib}:$LD_LIBRARY_PATH"\n'
                    f'exec "{cc}{suffix}" "$@"\n'
                )
            os.chmod(wrapper, 0o755)
            wrappers[suffix] = wrapper
        return wrappers[""]

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            cc_wrapper = (self._make_clang_wrapper(cc)
                          if cc and self._host_needs_clang_wrapper() else None)
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
            if cc_wrapper:
                content = re.sub(r"^c\s*=.*$", f"c = '{cc_wrapper}'", content, flags=re.M)
                content = re.sub(r"^cpp\s*=.*$", f"cpp = '{cc_wrapper}++'", content, flags=re.M)
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

    def _glib_libintl_link_args(self):
        # OHOS has no libc gettext/intl; glib2's .pc carries -lintl and static
        # linking needs the package's libintl.a passed explicitly
        # (gupnp-av / atk 2.38.0.1.1 precedent).
        if self.settings.os != "OHOS":
            return []
        for dependency in self.dependencies.host.values():
            for library_name in ("libintl.a", "libintl.so"):
                library_path = os.path.join(dependency.package_folder, "lib", library_name)
                if os.path.isfile(library_path):
                    return [library_path.replace("\\", "/")]
        return []

    def _sdk_llvm_libdir(self):
        dirs = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        for d in reversed(dirs):
            if os.path.isdir(d):
                return d
        return None
