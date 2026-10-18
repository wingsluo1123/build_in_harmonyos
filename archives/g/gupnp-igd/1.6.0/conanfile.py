#!/usr/bin/env python3
"""Conan recipe — gupnp-igd 1.6.0 (Meson).

GUPnP IGD — a GObject-based library implementing the UPnP Internet Gateway
Device port-mapping protocol (Simple IGD), part of the GUPnP stack on top
of gupnp. Adapted to HarmonyOS PC (aarch64, musl, clang).

Build/downstream handling inherits the verified approaches of the same
GLib meson stack (gssdp 1.6.6 / gupnp 1.6.10):
  - static-only glib2 on ohpcd -> single GObject copy doctrine (g_* stay
    UND and resolve at runtime against the full glib symbol table
    exported by libsoup-3.0.so);
  - never strip shared libraries (embedded .codesign hash breaks, dlopen
    Permission denied);
  - meson install rewrites DT_RUNPATH -> overwrite installed .so with the
    build-tree artifact.

gupnp-igd specifics (see notes.md):
  - no source patch needed: unlike gupnp/gssdp, this library never touches
    netlink — the two C units only include arpa/inet.h, netinet/in.h,
    sys/types.h, sys/socket.h and string.h, all fine in the OHOS musl
    sysroot;
  - every glib/gio symbol referenced by the sources is either a macro or
    a static inline (g_warning -> g_log; g_atomic_int_*) or exported by
    libsoup-3.0.so (verified with nm against the published stack), so no
    minimal-members glib archive is required (unlike gupnp 1.6.10);
  - subprojects/gupnp-1.6.wrap is removed in source() to rule out any
    wrap download attempt on network-restricted CI workers. Meson only
    auto-falls-back to a subproject whose wrap has a [provide] section,
    and this one has none — the removal is defence in depth and touches
    no build input of the library itself.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.meson import Meson, MesonToolchain

# glib static-lib tokens that must NEVER reach a link command line (the
# single-copy GObject doctrine). See gssdp 1.6.6 notes for the SIGABRT root
# cause analysis behind this list.
GLIB_STATIC_TOKENS = {
    "-lglib-2.0", "-lgobject-2.0", "-lgio-2.0", "-lgmodule-2.0",
    "-lgthread-2.0", "-lffi", "-lintl",
}


class GupnpIgdConan(ConanFile):
    name = "gupnp-igd"
    version = "1.6.0"
    description = "GUPnP IGD — GObject-based UPnP Internet Gateway Device (Simple IGD) library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gupnp-igd"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gupnp-igd meson.build deps: glib-2.0 / gobject-2.0 / gthread-2.0
        # (all modules of the glib2 package), gupnp-1.6 >= 1.6.0 (gupnp) and
        # gssdp-1.6 >= 1.6.0 (gssdp).
        # libxml2 is NOT directly requested by the upstream meson.build but
        # must be declared here: the PkgConfigDeps-generated gupnp-1.6.pc
        # carries libxml-2.0 in its Requires closure, and the .pc file is
        # only reliably written for explicit requires (same rationale as the
        # gupnp 1.6.10 recipe which also declares it explicitly).
        # ⚠️ zlib root-level override pins the PIC variant (1.3.1.1): the
        # published zlib/1.3.1 libz.a is not -fPIC and breaks when linked
        # into a shared .so through the static glib2 chain. Same rationale
        # as gssdp 1.6.6 / gupnp 1.6.10.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib2/2.88.0")
        # Match the exact libsoup3 revision gssdp/1.6.6 and gupnp/1.6.10
        # were built against — otherwise the graph resolves two libsoup3
        # recipe revisions.
        self.requires("libsoup3/3.6.5-r1")
        self.requires("gssdp/1.6.6")
        self.requires("gupnp/1.6.10")
        self.requires("libxml2/2.15.3.1")

    def build_requirements(self):
        # meson probes `ninja --version` at configure time; the build profile
        # PATH already carries a static ninja on this host and CI workers ship
        # their own. Do NOT tool_require the registry ninja (needs
        # libc++_shared.so at load time and fails a clean-env probe) — same
        # decision as gssdp 1.6.6 / gupnp 1.6.10.
        pass

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The tarball ships subprojects/gupnp-1.6.wrap ([wrap-git] only, no
        # [provide] section, pinning gupnp-1.6.3 from gitlab). Meson would
        # never auto-fall-back to it while pkg-config resolves gupnp-1.6,
        # but remove it anyway so a network-restricted CI worker can never
        # even attempt the git clone (build_timeouts / offline discipline).
        rmdir(self, os.path.join(self.source_folder, "subprojects"))

    # ------------------------------------------------------------------ #
    # pkg-config surgery helpers                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _write(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _build_glib2_pc_fix(self, glib2_pkg, pc_fix_dir):
        """Copies of the glib2 package .pc files with prefix fixed to the real
        package folder, Libs stripped and libffi dropped from Requires.

        The published glib2 package installs its .pc files with prefix=/, so
        Cflags/Libs resolve to /include and /lib. libffi is only reachable via
        the raw glib2 .pc whose own prefix is broken (-L//lib -lffi,
        unresolvable at link time) and nothing needs to link libffi: GObject
        stays dynamic via libsoup-3.0.so (single-copy doctrine).
        """
        src_dir = os.path.join(glib2_pkg, "lib", "pkgconfig")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for pc in os.listdir(src_dir):
            if not pc.endswith(".pc"):
                continue
            text = self._read(os.path.join(src_dir, pc))
            text = re.sub(r"^prefix=.*$", "prefix={}".format(glib2_pkg), text,
                          count=1, flags=re.M)
            text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
            text = re.sub(r"^Libs\.private:.*$", "Libs.private: ", text, flags=re.M)

            def _drop_libffi(match):
                toks = [t.strip() for t in match.group(1).split(",")]
                toks = [t for t in toks if t and t != "libffi"]
                return "Requires: " + ", ".join(toks)

            text = re.sub(r"^Requires:(.*)$", _drop_libffi, text, flags=re.M)
            self._write(os.path.join(pc_fix_dir, pc), text)

    def _strip_glib_from_generated_pc(self, name):
        """Token-level removal of the static-glib list that PkgConfigDeps
        inlines into the generated .pc files (the published libsoup3 recipe
        appends the whole glib static lib list to its cpp_info.libs). Keeps
        -lsoup-3.0 / -lgssdp-1.6 / -lgupnp-1.6 / -lxml2 themselves.
        """
        path = os.path.join(self.generators_folder, name)
        if not os.path.isfile(path):
            return
        out = []
        for line in self._read(path).splitlines(True):
            match = re.match(r"^(Libs:)(.*)$", line)
            if match:
                kept = [t for t in match.group(2).split()
                        if t not in GLIB_STATIC_TOKENS]
                line = "Libs: " + " ".join(kept) + "\n"
            out.append(line)
        self._write(path, "".join(out))

    # ------------------------------------------------------------------ #

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # not on its PATH; meson probes them and aborts. Pin the real tools by
        # absolute PATH and drop the broken env values (same as
        # glib2/2.88.0, libsoup3/3.6.5-r1, gssdp/1.6.6, gupnp/1.6.10).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name)
                 for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not in PATH: {}".format(", ".join(missing)))

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ never strip shared libraries: the OHOS loader verifies the
        # embedded .codesign hash against the file content; strip rewrites the
        # .so and dlopen fails with Permission denied (libsoup3 evidence).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = \
            "shared" if self.options.shared else "static"
        # gupnp-igd meson options: introspection defaults to TRUE upstream
        # and needs gobject-introspection (native tool, unavailable when
        # cross building) — must be disabled EXPLICITLY; gtk_doc defaults to
        # false upstream but is pinned anyway for determinism.
        for opt in ("introspection", "gtk_doc"):
            tc.project_options[opt] = "false"

        glib2 = self.dependencies.get("glib2")
        if not (glib2 and glib2.package_folder):
            raise ConanInvalidConfiguration("glib2 dependency not resolved")
        glib2_pkg = glib2.package_folder

        # 1) glib2 .pc copies with fixed prefix / stripped Libs / no libffi.
        pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
        self._build_glib2_pc_fix(glib2_pkg, pc_fix_dir)

        # 2) generators post-processing (PkgConfigDeps output):
        #    - glib-2.0.pc: Libs must not carry the static-glib list; the
        #      Requires line is emptied as well so the pcre2/zlib static
        #      archives of the glib2 package never enter the link either
        #      (gupnp 1.6.10 precedent).
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            text = self._read(glib_pc)
            text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
            text = re.sub(r"^Requires:.*$", "Requires: ", text, flags=re.M)
            self._write(glib_pc, text)
        #    - libsoup-3.0.pc / gssdp-1.6.pc / gupnp-1.6.pc / libxml-2.0.pc:
        #      token-strip the inlined static-glib list (keeps -lsoup-3.0 /
        #      -lgssdp-1.6 / -lgupnp-1.6 / -lxml2 and system libs). The
        #      Requires closures stay intact so the link line still collects
        #      the soup/gssdp/gupnp/xml shared objects through the closure.
        for name in ("libsoup-3.0.pc", "gssdp-1.6.pc", "gupnp-1.6.pc",
                     "libxml-2.0.pc"):
            self._strip_glib_from_generated_pc(name)

        # meson needs the gobject-2.0/gthread-2.0 modules of glib2 that
        # PkgConfigDeps does not generate (it only writes one glib-2.0.pc for
        # the whole glib2 package). Prepend the fixed copies so the broken
        # prefix=/ raw ones are never preferred.
        extra_pc = [pc_fix_dir, os.path.join(glib2_pkg, "lib", "pkgconfig")]
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)

        # gnome.genmarshal() in libgupnp-igd/meson.build runs glib-genmarshal
        # at build time: pin the glib2 package tools via PATH + the meson
        # native-file [binaries] section (gssdp/gupnp precedent).
        glib_bin = os.path.join(glib2_pkg, "bin")
        if os.path.isdir(glib_bin):
            self.buildenv_info.prepend_path("PATH", glib_bin)
            for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                         "glib-compile-resources", "glib-compile-schemas"):
                tool_path = os.path.join(glib_bin, tool)
                if os.path.isfile(tool_path):
                    tc.binaries[tool] = tool_path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not "
                "runnable on the build host)")
        else:
            if hasattr(os, "uname") and \
                    os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    # The single upstream test drives a full simulated IGD
                    # device over loopback (SSDP discovery + SOAP action
                    # round-trips) for 11 TAP subtests; run it natively on
                    # the OHOS device with a generous timeout. CI workers run
                    # many parallel builds and can be several times slower
                    # than an idle host — the default 30s x 16 = 480s was
                    # observed to be insufficient on a loaded worker
                    # (build #93350: TIMEOUT killed by SIGTERM at 480.03s
                    # while the suite passes in ~1-2 min locally), so use a
                    # 48x multiplier (1440s), still well inside the default
                    # 3600s conan create budget.
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=48 '
                        "--no-rebuild".format(build_folder)
                    )

                meson.test = _ohos_meson_test
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # ⚠️ meson install cleans DT_RUNPATH by overwriting bytes inside
        # .dynstr and dropping the entry, which invalidates the embedded
        # .codesign hash -> dlopen Permission denied (libsoup3 evidence).
        # Overwrite the installed .so with the untouched build-tree artifact.
        if self.options.shared:
            _lib = "libgupnp-igd-1.6.so.0.0.0"
            _src = os.path.join(self.build_folder, "libgupnp-igd", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["gupnp-igd-1.6"]
        # headers install to include/gupnp-igd-1.6/libgupnp-igd/; consumers
        # use #include <libgupnp-igd/gupnp-simple-igd.h>
        self.cpp_info.includedirs = ["include/gupnp-igd-1.6"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # ⚠️ CMakeDeps generates empty data for TRANSITIVE deps (conan 2.29),
        # so expose the dependency include dirs here to let consumers compile:
        # gupnp-igd public headers include glib/gobject headers, and typical
        # consumers also compile against gupnp/gssdp/soup/libxml2 headers.
        # libs stay "gupnp-igd-1.6" only — glib/gobject/gupnp/soup/xml symbols
        # resolve through the NEEDED chain (single GObject copy).
        for depname in ("glib2", "libsoup3", "gssdp", "gupnp", "libxml2"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                self.cpp_info.includedirs.append(
                    os.path.join(dep.package_folder, "include"))
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                if depname == "glib2":
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "include", "glib-2.0"))
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "lib", "glib-2.0",
                                     "include"))
                self.cpp_info.libdirs.append(
                    os.path.join(dep.package_folder, "lib"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # PkgConfigDeps picks up pkg_config_name; CMakeDeps needs the cmake
        # names explicitly (same as gssdp/gupnp).
        self.cpp_info.set_property("pkg_config_name", "gupnp-igd-1.6")
        self.cpp_info.set_property("cmake_file_name", "gupnp-igd-1.6")
        self.cpp_info.set_property("cmake_target_name", "gupnp-igd-1.6::gupnp-igd-1.6")
