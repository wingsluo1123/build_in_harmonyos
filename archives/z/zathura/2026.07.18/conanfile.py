#!/usr/bin/env python3
"""Conan recipe for zathura — highly customizable document viewer.

zathura 2026.07.18 is the version that reworked its whole GTK layer: the
``girara-gtk/`` compatibility shim is compiled into the ``libzathura`` helper
library and the GUI now targets **GTK4** (``dependency('gtk4', version:
'>=4.12')``), not GTK3.  The earlier sibling recipe in this repo
(``archives/z/zathura/2026.05.20``) declared ``gtk/3.24.43`` and consequently
never configured; this recipe uses the published ``gtk4/4.22.4`` package.

Extra runtime dependencies introduced by this release: ``libmagic`` (content
type sniffing), ``libxxhash`` (document cache hashing) and ``sqlite3``
(database backend).
"""
import os
import re
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


# --------------------------------------------------------------------------- #
# glib build tools                                                            #
# --------------------------------------------------------------------------- #
# meson's gnome module (used by data/meson.build for gnome.compile_resources)
# execs glib-compile-resources during `ninja`.  Two OHOS-specific problems make
# that fail, and both have to be fixed together:
#
#   1. execve() on the copy inside the Conan package cache returns EPERM,
#      because meson's install step (and Conan's own packaging) drops the
#      `.codesign` section OHOS requires.  Every glib tool has to be copied
#      out and re-signed before it can be executed.
#   2. Conan does not export LD_LIBRARY_PATH for the build, so the tool starts
#      but the dynamic loader cannot find libgio-2.0.so.0 / libglib-2.0.so.0 /
#      libgobject-2.0.so.0 / libintl.so.8 and every glib symbol fails to
#      relocate ("Error relocating ...: g_clear_error: symbol not found"),
#      which surfaces as `FAILED: [code=127] data/resources.c`.
#
# Same fix, same reason, as archives/g/gspell/1.14.4 and archives/g/gtk/3.24.43
# (both built against this same glib).
HNP_BIN = "/data/service/hnp/bin"
PYTHON3 = os.path.realpath(sys.executable)

# glib's python-script tools need an explicit interpreter: the shebang they
# ship points at a build-machine path that does not exist in the CI sandbox.
GLIB_PYTHON_TOOLS = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen")
# ELF tools: they must be copied out of the package cache and re-signed.
GLIB_ELF_TOOLS = (
    "glib-compile-resources",
    "glib-compile-schemas",
    "gobject-query",
    "gio-querymodules",
)


def _inject_llvm_binutils(conanfile):
    """Put llvm-ar/llvm-ranlib into the generated meson native file.

    conan's MesonToolchain does not emit ``ar``/``ranlib``.  meson then probes
    the bare name ``llvm-ar`` on PATH; when the clang toolchain lives in a
    directory that is not on PATH, configure aborts with
    ``Unknown linker(s): [['llvm-ar']]``.  Derive the full paths from the C
    compiler's own directory and inject them.

    ``pkg-config`` is injected at the same time: a cross build requires it to
    be named in the machine file, otherwise meson reports ``Found pkg-config:
    NO`` and every ``dependency()`` lookup fails.
    """
    ce = conanfile.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = ce.get("c") or ""
    bindir = os.path.dirname(cc) if os.path.sep in cc else ""
    if not bindir:
        return
    ar = ranlib = None
    cand = os.path.join(bindir, "llvm-ar")
    if os.path.isfile(cand):
        ar = cand
        cand_rl = os.path.join(bindir, "llvm-ranlib")
        if os.path.isfile(cand_rl):
            ranlib = cand_rl
    # Patch whichever machine file meson will actually read.  Building for
    # OHOS is a cross build, so MesonToolchain writes conan_meson_cross.ini and
    # passes it as --cross-file; conan_meson_native.ini is also written but is
    # not used.  Injecting into the native file alone silently has no effect.
    for name in ("conan_meson_cross.ini", "conan_meson_native.ini"):
        machine = os.path.join(conanfile.generators_folder, name)
        if os.path.isfile(machine):
            _patch_machine_file(conanfile, machine, ar, ranlib)


def _patch_machine_file(conanfile, machine, ar, ranlib):
    """Add ar/ranlib/pkg-config to one meson machine file's [binaries] section."""
    with open(machine) as fh:
        content = fh.read()
    if "[binaries]" not in content:
        return
    ins = ""
    if ar and "\nar =" not in content:
        ins += "ar = '%s'\n" % ar
    if ar and ranlib and "\nranlib =" not in content:
        ins += "ranlib = '%s'\n" % ranlib
    # A cross build needs pkg-config named explicitly in the machine file:
    # meson refuses the PATH default and aborts configure with "Pkg-config
    # binary missing from cross or native file, or env var undefined" ->
    # "Found pkg-config: NO", which surfaces as "Dependency lookup for girara
    # with method 'pkg-config' failed".
    pkg_config = conanfile.conf.get("tools.gnu:pkg_config", default=None)
    if not pkg_config or not os.path.isfile(str(pkg_config)):
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
    if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
        ins += "pkg-config = '%s'\n" % pkg_config
    if not ins:
        return
    content = content.replace("[binaries]\n", "[binaries]\n" + ins, 1)
    with open(machine, "w") as fh:
        fh.write(content)
    conanfile.output.info("patched %s: %s"
                          % (os.path.basename(machine),
                             " ".join(ins.split())))


class ZathuraConan(ConanFile):
    name = "zathura"
    version = "2026.07.18"
    package_type = "application"
    description = ("A highly customizable and functional document viewer "
                   "with a minimalistic interface")
    license = "Zlib"
    homepage = "https://pwmt.org/projects/zathura"
    url = "https://github.com/pwmt/zathura"

    settings = "os", "arch", "compiler", "build_type"
    # zathura is an application (CLI + plugin API headers) and has no library
    # of its own.  conan removes both `shared` and `fPIC` for package_type
    # "application", so declaring them makes the package invalid
    # ("Invalid: 'options.fPIC' value not defined").  Declaring `shared` was
    # also actively harmful: default_options propagation broadcast
    # {"shared": True} to every dependency, forcing harfbuzz to shared=False
    # and leaving the graph asking for an unpublished package id
    # ("Options conflicts: harfbuzz/14.2.0.1->shared=False").
    options = {}

    def config_options(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # 2026.07.07.1 is the revision that survives being rebuilt against this
        # graph's glib (which the GTK4 stack forces via the override below): the
        # previous revision aliased gobject/gio onto dependency('glib-2.0') and
        # therefore linked only -lglib-2.0, leaving every g_type_*/g_object_*
        # symbol undefined.  2026.07.07.1 looks each module up by its own
        # pkg-config name and materialises the glib .pc files PkgConfigDeps
        # omits.  See PR !14001.
        self.requires("girara/2026.07.07.1")
        # 2026.07.x moved the GUI layer to GTK4; gtk4/4.22.4 satisfies
        # meson's dependency('gtk4', version: '>=4.12').
        self.requires("gtk4/4.22.4")
        # glib: girara pins an exact glib/2.84.0 while pango/1.56.4 (pulled in
        # by gtk4) pins glib/2.84.0.1.  Because girara pins an exact version
        # rather than a range, conan aborts with "Version conflict: Conflict
        # between glib/2.84.0.1 and glib/2.84.0 in the graph" unless the
        # consumer unifies the graph itself.  Unify on 2.84.0.1.1, the signed
        # revision the gtk4 recipe itself overrides to.  The GTK4 stack
        # (gtk4/pango/harfbuzz/gdk-pixbuf/...) is built against it and against
        # pcre2/10.45, so unifying DOWN to girara's 2.84.0 would instead
        # invalidate every one of those package ids; rebuilding girara is the
        # smaller cost and is what this repository does for its GTK4 consumers.
        # girara/2026.07.07.1 exists precisely so that this rebuild succeeds
        # (see PR !14001).
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # zlib / fontconfig: pinned to the revisions the gtk4 recipe itself
        # overrides to, preventing newer transitive versions from breaking the
        # graph (same choice as zenity/4.2.2 and libadwaita/1.2.0).
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        # harfbuzz: pango pins 14.2.0.1, whose published binary was built
        # against a different glib and therefore misses once the graph is
        # unified (harfbuzz/14.2.0.1:1b5bfb05... Missing).  14.2.0.1.1.1 is the
        # revision the gtk4 consumers in this repo override to.
        self.requires("harfbuzz/14.2.0.1.1.1", override=True)
        self.requires("json-glib/1.10.6")
        self.requires("cairo/1.18.4")
        self.requires("libmagic/5.48")
        self.requires("sqlite3/3.49.1")
        self.requires("xxhash/0.8.3")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._provide_glib_pc_files()
        staged_tools = self._prepare_glib_build_tools()
        self._inject_glib_tool_variables(staged_tools)
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        # upstream has no "tests" option; the headless suite is driven by
        # tests-x11/tests-wayland, which need xvfb/weston and are therefore
        # unavailable in the cross build.
        tc.project_options["tests-x11"] = "disabled"
        tc.project_options["tests-wayland"] = "disabled"
        tc.project_options["manpages"] = "disabled"
        tc.project_options["convert-icon"] = "disabled"
        tc.project_options["seccomp"] = "disabled"
        tc.project_options["landlock"] = "disabled"
        tc.project_options["synctex"] = "disabled"
        # upstream default_options sets c_std=c23; CI clang 15 only knows the
        # C23 draft alias c2x.
        tc.project_options["c_std"] = "c2x"
        tc.generate()
        _inject_llvm_binutils(self)
        # NOTE: _setup_build_ld_library_path() is deliberately NOT called
        # here.  It returns EnvVars that only take effect when applied,
        # and save_script() writes a standalone script that conanbuild.sh
        # does not chain.  Calling it here would be a silent no-op; the
        # real application happens in build().

    def _provide_glib_pc_files(self):
        """Materialise the glib .pc files meson looks up but Conan does not emit.

        zathura's meson.build looks up several glib modules by pkg-config name
        with a >=2.84 version constraint: gio-unix-2.0, gmodule-no-export-2.0,
        gthread-2.0 and friends.  The glib Conan package ships all of those .pc
        files, but PkgConfigDeps only emits .pc files for the components a
        recipe declares as direct requirements.  For anything it does not emit,
        meson falls back to whatever .pc the build machine has on its default
        pkg-config search path -- typically an older host glib (2.72.4), which
        then fails the version check.

        Copy every .pc file from the glib package we actually depend on into the
        generator folder, which is already on PKG_CONFIG_PATH.  Only files that
        PkgConfigDeps did not already emit are written, so Conan's own component
        metadata always wins.
        """
        try:
            glib = self.dependencies["glib"]
        except KeyError:
            return
        root = glib.package_folder
        if not root:
            return
        srcdir = os.path.join(root, "lib", "pkgconfig")
        if not os.path.isdir(srcdir):
            return
        copied, merged = [], []
        for name in sorted(os.listdir(srcdir)):
            if not name.endswith(".pc"):
                continue
            dst = os.path.join(self.generators_folder, name)
            with open(os.path.join(srcdir, name)) as fh:
                content = fh.read()
            # the packaged .pc files carry the original install prefix; pin them
            # to this glib package so a lookup can never drift to the host
            content = re.sub(r"^prefix=.*$",
                             "prefix=%s" % root.replace("\\", "/"),
                             content, count=1, flags=re.M)
            if not os.path.exists(dst):
                with open(dst, "w") as fh:
                    fh.write(content)
                copied.append(name)
                continue
            # Keep Conan's component .pc (its libs/cflags/Requires stay
            # authoritative) but graft in every variable it does not carry,
            # overriding version=, because gnome.compile_resources() in
            # data/meson.build reads the tool paths (glib-compile-resources,
            # gdbus-codegen, ...) out of gio-2.0 via get_variable(pkgconfig:)
            # and meson builds a *build-time* dependency on gio-2.0.  Conan's
            # component gio-2.0.pc carries neither those variables nor the
            # glib release version, so meson aborts with "Could not get
            # pkg-config variable and no default provided for
            # <PkgConfigDependency gio-2.0>".  These entries are tool paths and
            # the glib release the binaries come from, not dependency
            # metadata, so grafting them cannot change what gets linked.
            with open(dst) as fh:
                generated = fh.read()
            existing = set()
            for ln in generated.splitlines():
                m = re.match(r"^([a-z_][a-z0-9_]*)=", ln)
                if m:
                    existing.add(m.group(1))
            wanted = []
            for ln in content.splitlines():
                m = re.match(r"^([a-z_][a-z0-9_]*)=", ln)
                if m and m.group(1) not in existing:
                    wanted.append(ln)
            if wanted:
                with open(dst, "a") as fh:
                    fh.write("\n".join(wanted) + "\n")
                merged.append(name)
        if copied:
            self.output.info(
                "provided %d glib .pc file(s) not emitted by PkgConfigDeps: %s"
                % (len(copied), " ".join(copied)))
        if merged:
            self.output.info(
                "merged glib tool variables into %d .pc file(s): %s"
                % (len(merged), " ".join(merged)))


    # ------------------------------------------------------------------
    # OHOS worker constraints (CI builds #66697 / #66737)
    # ------------------------------------------------------------------
    def _signing_tools(self):
        """Locate the OHOS ELF signing tools on this machine.

        The OHOS toolchain ships llvm-objcopy and binary-sign-tool next to the
        compiler (tools.build:compiler_executables.c); the CI workers
        additionally expose them in /data/service/hnp/bin.  Return (None, None)
        when neither location has them, so callers can decide whether that is
        fatal (packaging) or merely a warning (build tools).
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        for cand in (bindir, "/data/service/hnp/bin"):
            if not cand:
                continue
            objcopy = os.path.join(cand, "llvm-objcopy")
            signer = os.path.join(cand, "binary-sign-tool")
            if os.path.isfile(objcopy) and os.path.isfile(signer):
                return objcopy, signer
        return None, None


    def _build_environment(self):
        """Build environment for the meson/ninja subprocesses.

        i18n.merge_file(type: 'xml') in data/meson.build shells out to
        msgfmt --xml, and msgfmt only looks for the gettext ITS localisation
        rules under $XDG_DATA_DIRS/gettext/its.  The gettext that ships with
        the OHOS worker keeps those rules inside its own installation prefix
        instead, so CI build #66737 aborted with::

            msgfmt: cannot locate ITS rules for ../data/org.pwmt.zathura.metainfo.xml.in

        Stage the rules into the build folder and put that folder on
        XDG_DATA_DIRS (the same fix the glade recipe uses).  When the rules are
        absent the variable is simply not injected.
        """
        env = Environment()
        its_src = ("/data/service/hnp/gettext.org/gettext_0.26/share/"
                   "gettext-0.26/its")
        share = os.path.join(self.build_folder, "test-data", "share")
        its_dst = os.path.join(share, "gettext", "its")
        if os.path.isdir(its_src) and not (os.path.isdir(its_dst) and os.listdir(its_dst)):
            os.makedirs(its_dst, exist_ok=True)
            for name in os.listdir(its_src):
                rule = os.path.join(its_src, name)
                if os.path.isfile(rule):
                    shutil.copyfile(rule, os.path.join(its_dst, name))
        if os.path.isdir(its_dst) and os.listdir(its_dst):
            env.prepend_path("XDG_DATA_DIRS", share)
        return env

    # ------------------------------------------------------------------ #
    # glib build tool staging                                             #
    # ------------------------------------------------------------------ #
    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _ohos_tool(self, name):
        """Locate an OHOS signing tool.

        The CI worker keeps llvm-objcopy/binary-sign-tool in
        /data/service/hnp/bin, but that directory is only a partial shim on
        other machines, so the compiler's own bindir is tried first — it
        carries both tools next to clang.  HNP_BIN stays as the fallback.
        """
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict)
        cc = ce.get("c") or ""
        if os.path.sep in cc:
            cand = os.path.join(os.path.dirname(cc), name)
            if os.path.isfile(cand):
                return cand
        cand = os.path.join(HNP_BIN, name)
        return cand if os.path.isfile(cand) else None

    def _sign_elf(self, binary):
        """Make an ELF from the package cache executable under OHOS.

        The cached binaries still carry a `.codesign` section produced on
        another machine, which OHOS treats as a stale signature and refuses to
        execve (EPERM, shell exit code 126).  Drop it and self-sign.

        Idempotent: `binary-sign-tool` refuses to sign a file that already has
        a `.codesign` section ("WriteCodeSignBlock error / .codesign section
        already exists"), so the strip is retried and its absence is tolerated
        rather than aborting the build.
        """
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        if objcopy:
            self.run("%s --remove-section .codesign %s 2>/dev/null || true"
                     % (shlex.quote(objcopy), shlex.quote(binary)),
                     ignore_errors=True)
        if not signer:
            raise ConanException(
                "no binary-sign-tool available; %s cannot be made executable "
                "on OHOS" % binary)
        ret = self.run(shlex.join([signer, "sign", "-inFile", binary,
                                   "-outFile", binary, "-selfSign", "1"]),
                       ignore_errors=True)
        if ret != 0:
            # Fatal on purpose: an un-signed copy is copied into the staged
            # tool folder and referenced from the .pc files, so a failure here
            # would only surface much later as an opaque "FAILED: [code=126]".
            # _sign_ohos_binaries() raises for the same reason.
            raise ConanException(
                "binary-sign-tool failed with exit code %d for %s" % (ret, binary))

    def _prepare_glib_build_tools(self):
        """Stage glib's build tools into the build folder.

        Returns {tool name: absolute path of the staged copy}.
        """
        try:
            glib_pkg = self.dependencies["glib"]
        except KeyError:
            return {}
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        quote = lambda s: "'" + str(s).replace("'", "'\\''") + "'"

        staged = {}
        # python tools: a sh wrapper that names the interpreter explicitly,
        # because the packaged shebang points outside the CI sandbox.
        for tool in GLIB_PYTHON_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            wrapper = os.path.join(tools_folder, tool)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\nexec %s %s \"$@\"\n"
                             % (quote(PYTHON3), quote(src)))
            os.chmod(wrapper, 0o755)
            staged[tool] = wrapper

        # ELF tools: copy out of the cache, then re-sign.
        for tool in GLIB_ELF_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            target = os.path.join(tools_folder, tool)
            shutil.copyfile(src, target)
            os.chmod(target, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(target)
            staged[tool] = target
        if staged:
            self.output.info("staged glib build tools: %s"
                             % " ".join(sorted(staged)))
        return staged

    def _inject_glib_tool_variables(self, staged_tools):
        """Point the glib .pc tool variables at the staged copies.

        gnome.compile_resources() resolves glib_compile_resources out of
        gio-2.0.pc via get_variable(pkgconfig:).  Without this the variable is
        missing and meson aborts with "Could not get pkg-config variable and no
        default provided for <PkgConfigDependency gio-2.0>"; with it, meson
        records the staged (executable, correctly signed) path as a build-time
        dependency.
        """
        if not staged_tools:
            return
        gens = self.generators_folder
        tool_map = {
            "gio-2.0.pc": (
                "glib_compile_resources",
                "glib_compile_schemas",
                "gio_querymodules",
                "gdbus_codegen",
            ),
            "glib-2.0.pc": (
                "glib_mkenums",
                "glib_genmarshal",
            ),
        }
        for pc_name, variables in tool_map.items():
            pc_path = os.path.join(gens, pc_name)
            if not os.path.isfile(pc_path):
                continue
            with open(pc_path, encoding="utf-8") as fh:
                text = fh.read()
            # Override, do not skip: PkgConfigDeps already emits these
            # variables pointing at ${bindir} inside the package cache, and a
            # tool executed from there dies with EPERM (exit 126) because its
            # stale .codesign has to be re-signed first.  Rewriting the value
            # is what actually redirects meson at the staged copy.
            rewrote, added = [], []
            for var in variables:
                path = staged_tools.get(var.replace("_", "-"))
                if not path:
                    continue
                value = path.replace(os.sep, "/")
                pattern = re.compile(r"^%s[ \t]*=.*$" % re.escape(var), re.M)
                if pattern.search(text):
                    if pattern.search(text).group(0).strip() != "%s=%s" % (var, value):
                        text = pattern.sub("%s=%s" % (var, value), text)
                        rewrote.append(var)
                else:
                    text += "\n%s=%s" % (var, value)
                    added.append(var)
            if not rewrote and not added:
                continue
            with open(pc_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            self.output.info("tool vars in %s: rewrote [%s] added [%s]"
                             % (pc_name, " ".join(rewrote), " ".join(added)))

    def _setup_build_ld_library_path(self):
        """Put dependency bindirs/libdirs on PATH/LD_LIBRARY_PATH for the build.

        meson's gnome module execs glib-compile-resources during `ninja`.  On
        OHOS /data/service/hnp/bin holds broken symlinks to the system glib
        tools, and Conan does not set LD_LIBRARY_PATH, so without this the tool
        aborts with "Error loading shared library libgio-2.0.so.0" and every
        glib symbol fails to relocate.
        """
        from conan.tools.env import Environment
        env = Environment()
        seen = set()

        def add_libdir(path):
            if not path or not os.path.isabs(path):
                return
            path = os.path.normpath(path)
            if path in seen:
                return
            seen.add(path)
            env.prepend_path("LD_LIBRARY_PATH", path)

        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                add_libdir(libdir)
            for component in dep.cpp_info.components.values():
                for libdir in component.libdirs:
                    add_libdir(libdir)
        # Only the staged glib tools go on PATH.  Prepending every dependency
        # bindir would also inject the relative entries some packages declare
        # (a bare "bin"), and a relative entry makes meson's pkg-config probe
        # fail with "Found pkg-config: NO / Pkg-config for machine host machine
        # not found", aborting configure before any target is built.
        env.prepend_path("PATH", self._glib_tools_folder())
        # PKG_CONFIG_PATH must point at the generators folder, otherwise
        # pkg-config answers from the *host* glib (2.72.4 in
        # /usr/lib/x86_64-linux-gnu/pkgconfig) and meson reads its
        # glib_compile_resources variable, i.e. /usr/bin/glib-compile-resources.
        # On the OHOS worker that path is a broken symlink into
        # /data/service/hnp/bin, so ninja dies with exit code 126.
        pkgconfig_dirs = [self.generators_folder]
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                cand = os.path.join(libdir, "pkgconfig")
                if os.path.isdir(cand):
                    pkgconfig_dirs.append(cand)
        seen_pc, ordered = set(), []
        for pcdir in pkgconfig_dirs:
            pcdir = os.path.normpath(pcdir)
            if pcdir in seen_pc or not os.path.isdir(pcdir):
                continue
            seen_pc.add(pcdir)
            ordered.append(pcdir)
            env.prepend_path("PKG_CONFIG_PATH", pcdir)
        # PKG_CONFIG_LIBDIR *replaces* pkg-config's built-in search path, which
        # otherwise still contains /usr/lib/x86_64-linux-gnu/pkgconfig.  The
        # host glib living there answers gio-2.0 with version 2.72.4 and
        # glib_compile_resources=/usr/bin/glib-compile-resources; on the OHOS
        # worker that path is a broken link into /data/service/hnp/bin, which
        # is what fails the build with exit code 126.
        if ordered:
            env.define("PKG_CONFIG_LIBDIR", os.pathsep.join(ordered))
        env_vars = env.vars(self, scope="build")
        # No save_script() here on purpose: it would drop a standalone script in
        # the generators folder that nothing sources (conanbuild.sh does not
        # chain it), so it can only mislead whoever finds the file later.  The
        # caller applies the returned EnvVars directly.
        return env_vars

    def build(self):
        apply_conandata_patches(self)
        env = self._build_environment()
        # the staged glib tools need the dependency libdirs on LD_LIBRARY_PATH,
        # otherwise the loader cannot resolve libglib-2.0.so.0 / libgio-2.0.so.0
        # and every glib symbol fails to relocate (exit 127/126).
        tool_env = self._setup_build_ld_library_path()
        with env.vars(self).apply(), tool_env.apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        Meson(self).install()
        self._sign_ohos_binaries()

    def _sign_ohos_binaries(self):
        """Re-sign every installed .so and executable for OHOS.

        meson rewrites the rpath after linking, which drops the linker's
        self-signature; OHOS refuses to dlopen/exec unsigned artifacts, so
        strip the stale .codesign section and re-sign with binary-sign-tool.
        """
        if self.settings.os != "OHOS":
            return
        import glob
        targets = []
        for sub in ("lib", "bin"):
            root = os.path.join(self.package_folder, sub)
            targets += glob.glob(os.path.join(root, "**", "*.so"), recursive=True)
            targets += glob.glob(os.path.join(root, "**", "*.so.*"), recursive=True)
            for entry in glob.glob(os.path.join(root, "**", "*"), recursive=True):
                if os.path.isfile(entry) and os.access(entry, os.X_OK):
                    targets.append(entry)
        targets = sorted(set(targets))
        if not targets:
            return
        objcopy, signer = self._signing_tools()
        if not objcopy or not signer:
            raise ConanException(
                "OHOS signing tools (llvm-objcopy/binary-sign-tool) are "
                "unavailable in tools.build:compiler_executables and "
                "/data/service/hnp/bin")
        for target in targets:
            # shlex.join, matching _sign_elf(): these paths come from
            # tools.build:compiler_executables / HNP_BIN and CONAN_HOME-derived
            # folders, so hand-rolled double quotes are not sufficient escaping.
            ret = self.run(
                shlex.join([objcopy, "--remove-section", ".codesign", target]),
                ignore_errors=True)
            if ret != 0:
                self.output.warn(
                    "llvm-objcopy returned %d for %s (possibly no .codesign yet)"
                    % (ret, target))
            ret = self.run(
                shlex.join([signer, "sign", "-inFile", target,
                            "-outFile", target, "-selfSign", "1"]),
                ignore_errors=True)
            if ret != 0:
                raise ConanException(
                    "binary-sign-tool failed with exit code %d for %s"
                    % (ret, target))

    def package_info(self):
        # zathura ships a CLI plus the static helper library used by plugins;
        # the plugin API is exposed through headers + a pkg-config file.
        self.cpp_info.includedirs = ["include/zathura", "include"]
        self.cpp_info.set_property("cmake_file_name", "zathura")
        self.cpp_info.set_property("cmake_target_name", "zathura::zathura")
        self.cpp_info.set_property("pkg_config_name", "zathura")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
