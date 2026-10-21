#!/usr/bin/env python3
"""Conan recipe — krb5-auth-dialog 43.0 (GNOME Kerberos applet, GTK3).

Application package: builds the krb5-auth-dialog binary plus its runtime
plugins (dummy/afs/gnomelock; the pam plugin is disabled). The upstream
gcr-3 dependency is dropped in favour of GtkEntryBuffer (the registry only
ships gcr-base built with gtk=false, so GcrSecureEntryBuffer is not
available), help/ is skipped (gnome.yelp needs itstool/yelp-tools), and a
headless --version path is added before gtk_init so the CLI contract stays
verifiable on display-less OHOS.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Krb5AuthDialogConan(ConanFile):
    name = "krb5-auth-dialog"
    version = "43.0"
    description = "GNOME Kerberos credentials notification applet (GTK3)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/krb5-auth-dialog"
    url = "https://download.gnome.org/sources/krb5-auth-dialog/43/krb5-auth-dialog-43.0.tar.xz"
    package_type = "application"
    topics = ("kerberos", "gtk", "gnome")

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # gtk/3.24.43 pins glib/2.84.0.1 internally (avahi-ui 0.8 precedent);
        # glib is declared directly because upstream finds glib-2.0/gio/
        # gobject/gmodule through pkg-config.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("krb5/1.22.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")
        # po/ (i18n.gettext preset 'glib') and .desktop merging need msgfmt.
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("krb5-auth-dialog only builds on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # OHOS musl's libintl.h macro-maps gettext to g_libintl_*, but the
        # glib package's libintl.so exports only libintl_* symbols — the app
        # references g_libintl_* at link time. Inline-write the passthrough
        # wrapper (atk/2.36.0 E107 precedent: shutil write, not a patch, to
        # avoid Conan 2.x patch path resolution pitfalls).
        wrapper = os.path.join(self.source_folder, "src", "intl-wrapper.c")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(
                "/* g_libintl_* passthrough: OHOS musl libintl.h lacks gettext\n"
                " * declarations; return the msgid unchanged (English strings).\n"
                " * (atk 2.36.0 E107 pattern.) */\n"
                "#include <glib.h>\n"
                "char *g_libintl_gettext(const char *msgid) { return (char *)(msgid); }\n"
                "char *g_libintl_dgettext(const char *d, const char *m) { (void)d; return (char *)(m); }\n"
                "char *g_libintl_dcgettext(const char *d, const char *m, int c) { (void)d; (void)c; return (char *)(m); }\n"
                "char *g_libintl_ngettext(const char *m1, const char *m2, unsigned long n) { return (char *)((n == 1) ? m1 : m2); }\n"
                "char *g_libintl_dngettext(const char *d, const char *m1, const char *m2, unsigned long n) { (void)d; return (char *)((n == 1) ? m1 : m2); }\n"
                "char *g_libintl_dcngettext(const char *d, const char *m1, const char *m2, unsigned long n, int c) { (void)d; (void)c; return (char *)((n == 1) ? m1 : m2); }\n"
                "char *g_libintl_textdomain(const char *d) { (void)d; return (char *)(\"\"); }\n"
                "char *g_libintl_bindtextdomain(const char *d, const char *dir) { (void)d; (void)dir; return (char *)(\"\"); }\n"
                "char *g_libintl_bind_textdomain_codeset(const char *d, const char *cs) { (void)d; (void)cs; return (char *)(\"\"); }\n"
            )

    def generate(self):
        # OHOS worker 导出 AR/AS/STRIP/NM/RANLIB 为 llvm-* 裸名且不在 PATH（posix_spawn
        # 不搜索 PATH），meson 探测 archiver 时 `llvm-ar --version` 必失败——先剔除坏值
        # 再按绝对路径固定（appstream 1.2.0 / libxmlb / glib-networking 先例）。
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {
            name: shutil.which(name)
            for name in ("ar", "as", "strip", "nm", "ranlib")
        }
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options.update({
            # pam headers are not part of the dependency closure
            "pam-plugin": "disabled",
            # keep the krb5 preauth surface minimal for the applet use case
            "pkinit": "disabled",
            # flex/bison parser helper, off by upstream default
            "etpo": "disabled",
        })
        tc.generate()
        # gnome.compile_resources / gnome.compile_schemas shell out to
        # glib-compile-resources / glib-compile-schemas: RPATH-less ELFs from
        # the glib package bin/, wrapped with the package lib dir first on
        # LD_LIBRARY_PATH (libnma-gtk4 _glib_tool_launcher pattern).
        glib = self.dependencies["glib"]
        wrapdir = os.path.join(self.generators_folder, "glib-toolbin")
        os.makedirs(wrapdir, exist_ok=True)
        for tool in ("glib-compile-resources", "glib-compile-schemas"):
            real = os.path.join(glib.package_folder, "bin", tool)
            if not os.path.isfile(real):
                self.output.warning("glib build tool missing from package: %s" % tool)
                continue
            # Stage a writable copy and force a fresh selfSign: the conan
            # cache package folder is read-only and XPM refuses to exec the
            # downloaded ELF (EPERM) even though it carries a .codesign
            # section (zita-lrx 0.1.2 staging pattern).
            staged = os.path.join(wrapdir, tool + ".bin")
            if os.path.lexists(staged):
                os.unlink(staged)
            shutil.copy2(real, staged)
            self._self_sign(staged, force=True)
            wrapper = os.path.join(wrapdir, tool)
            with open(wrapper, "w", encoding="utf-8") as handle:
                handle.write(
                    "#!/bin/sh\n"
                    'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" exec "%s" "$@"\n'
                    % (os.path.join(glib.package_folder, "lib"), staged)
                )
            os.chmod(wrapper, 0o755)
        # meson setup probes `ninja --version` through PATH and VirtualBuildEnv
        # resets PATH: expose the host ninja (1.13.1, verified) through the
        # same toolbin channel the glib wrappers already ride (proven to be
        # found by meson). The registry ninja/1.12.1 package ships no usable
        # binary in cache, hence the wrapper instead of tool_requires.
        ninja_real = shutil.which("ninja") or "/usr/local/bin/ninja"
        if os.path.isfile(ninja_real):
            ninja_wrap = os.path.join(wrapdir, "ninja")
            with open(ninja_wrap, "w", encoding="utf-8") as handle:
                handle.write('#!/bin/sh\nexec "%s" "$@"\n' % ninja_real)
            os.chmod(ninja_wrap, 0o755)
        if os.listdir(wrapdir):
            env = Environment()
            env.prepend_path("PATH", wrapdir)
            env.vars(self, scope="build").save_script("krb5_glib_tools")
            # The meson gnome module locates its tools through pkg-config
            # variables — compile_schemas is queried on gio-2.0.pc and
            # compile_resources on gio-2.0.pc (observed) / glib-2.0.pc
            # (documented): inject both variables into both pc files so
            # either lookup path resolves to the wrapper (libnma-gtk4
            # _augment_glib_pkg_config_tools pattern).
            for pc_name in ("glib-2.0.pc", "gio-2.0.pc"):
                pc = os.path.join(self.generators_folder, pc_name)
                if not os.path.isfile(pc):
                    continue
                with open(pc, "a", encoding="utf-8") as handle:
                    for variable, tool in (
                        ("glib_compile_resources", "glib-compile-resources"),
                        ("glib_compile_schemas", "glib-compile-schemas"),
                    ):
                        wrapper = os.path.join(wrapdir, tool)
                        if os.path.isfile(wrapper):
                            handle.write("%s=%s\n" % (variable, wrapper))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # XPM refuses to exec/dlopen unsigned ELFs: sign the app and its
        # runtime-loaded plugin modules (glib selfSign precedent).
        for sub in ("bin", "lib"):
            base = os.path.join(self.package_folder, sub)
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for name in files:
                    path = os.path.join(root, name)
                    if name.endswith(".so") or os.access(path, os.X_OK):
                        self._self_sign(path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []

    def _self_sign(self, path, force=False):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            self.output.warning("OHOS signing tools missing; skip %s" % path)
            return
        sections = subprocess.run(
            [readelf, "-SW", path], check=True, capture_output=True, text=True, timeout=30
        ).stdout
        existing = sections.count(".codesign")
        if existing == 1 and not force:
            return
        if existing not in (0, 1):
            raise ConanInvalidConfiguration("invalid .codesign count on %s" % path)
        # force: strip the stale signature first (downloaded cache ELFs carry
        # a signature XPM refuses to honour — zita-lrx force-resign pattern).
        unsigned = path + ".unsigned"
        temporary = path + ".signed"
        for leftover in (unsigned, temporary):
            if os.path.lexists(leftover):
                raise ConanInvalidConfiguration("stale signing artifacts: %s" % leftover)
        sign_input = path
        try:
            if existing == 1:
                objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
                if not os.path.isfile(objcopy):
                    raise ConanInvalidConfiguration("llvm-objcopy missing")
                shutil.copy2(path, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    check=True, timeout=30,
                )
                sign_input = unsigned
            subprocess.run(
                [signer, "sign", "-inFile", sign_input, "-outFile", temporary, "-selfSign", "1"],
                check=True, timeout=60, stdout=sys.stderr,
            )
            signed = subprocess.run(
                [readelf, "-SW", temporary], check=True, capture_output=True, text=True, timeout=30
            ).stdout
            if signed.count(".codesign") != 1:
                raise ConanInvalidConfiguration("bad signature on %s" % path)
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(temporary, path)
        finally:
            for leftover in (temporary, unsigned):
                if os.path.lexists(leftover):
                    os.unlink(leftover)
