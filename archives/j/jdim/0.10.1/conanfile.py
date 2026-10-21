#!/usr/bin/env python3
"""Conan recipe — jdim 0.10.1 (GTK3 2ch browser, Autotools + GoogleTest).

Upstream: https://github.com/JDimproved/JDim  (tag JDim-v0.10.1, GPL-2.0-or-later)
Product:  the ``jdim`` GTK3 desktop application (bin/jdim).

Adaptation notes (the long form lives in notes.md):
  * The GitHub tag archive ships ``configure.ac`` + ``Makefile.am`` only (no
    ``configure``, no ``aclocal.m4``), so ``build()`` bootstraps the tree with
    ``autoreconf -fi``.  ``automake``/``libtool`` come from the build context
    (the CI worker has autoconf only, in /data/service/hnp/bin) and
    ``autoconf-archive`` supplies ``AX_CXX_COMPILE_STDCXX``.
  * ``PKG_CHECK_MODULES`` needs PkgConfigDeps' generated .pc files, and Conan
    does not export PKG_CONFIG_PATH into the conanbuild env, so the generators
    folder is handed to ``configure`` explicitly.  PkgConfigDeps would abort on
    gtkmm/3.24.11's ``components["gtkmm-3.0"].requires = [... "atkmm::atkmm-1.6"
    ...]`` because ohpcd's atkmm/2.28.4 exposes a root-level cpp_info without
    components, so ``_fix_dependency_components()`` mirrors atkmm's root info as
    that component before generating.  ``AC_CHECK_LIB`` (crypt/z/migemo) is
    covered by AutotoolsDeps' LDFLAGS.
  * ``gtest/1.17.0`` declares only the ``gtest`` component while upstream
    googletest also installs ``libgtest_main.a``; ``test/Makefile.am`` asks
    pkg-config for ``gtest_main >= 1.10.0``.  A ``gtest_main.pc`` shim is
    written next to the generated ``gtest.pc``.
  * ``config.status`` creates its scratch directory with
    ``umask 077 && mkdir``; on HMDFS that yields an unwritable setgid
    directory (E011/E114), so the generated ``configure`` is patched to
    ``umask 022`` before it runs.
  * The upstream suite (12 gtest source files, one ``check_PROGRAM``) really
    runs inside ``build()`` via ``make check``.  The machine-readable summary
    is printed as ``HMBS_UPSTREAM_TEST_RESULT=...`` for preflight collection.
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get,
                               replace_in_file, save)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# test/Makefile.am registers exactly one check_PROGRAM ("gtest_jdim") built
# from these 12 source files; the atomic case count is the number of TEST_F()
# registrations in those files at tag JDim-v0.10.1.
UPSTREAM_GTEST_SOURCES = 12
UPSTREAM_TEST_CASES = 531          # static TEST_F() registrations at the tag
# 5 of the 531 sit inside `#ifdef _POSIX_C_SOURCE` in gtest_jdlib_misctime.cpp and
# are compiled out in this configuration, so gtest registers 526.
UPSTREAM_REGISTERED_CASES = 526
UPSTREAM_PASS_BASELINE = 522       # documented platform baseline (see notes.md)
KNOWN_PLATFORM_FAILURES = (        # libc iconv substitutes '*' instead of failing
    "Iconv_ToAsciiFromUtf8.hiragana",
    "Iconv_ToAsciiFromUtf8.subdivision_flag",
    "MISC_UrlEncodeWithEncodingTest.encoded_to_eucjp",
    "MISC_UrlEncodePlusWithEncodingTest.encoded_to_eucjp",
)

# .pc names jdim's configure.ac asks for with PKG_CHECK_MODULES.
REQUIRED_PC = ("gtkmm-3.0", "gdkmm-3.0", "x11", "sm", "ice",
               "gnutls", "alsa", "gtest_main")


class JdimConan(ConanFile):
    name = "jdim"
    version = "0.10.1"
    description = "JDim — GTK3-based 2ch browser (JD improved)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/JDimproved/JDim"
    url = "https://github.com/JDimproved/JDim"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jdim is prepared for Linux/OHOS targets only, not %s" % self.settings.os
            )

    def requirements(self):
        # Everything configure.ac looks for with PKG_CHECK_MODULES / AC_CHECK_LIB.
        self.requires("gtkmm/3.24.11")            # gtkmm-3.0 >= 3.24.0
        self.requires("libx11/1.8.13")            # x11 (unconditional PKG_CHECK_MODULES)
        self.requires("libsm/1.2.6")              # sm >= 1.2  (--with-sessionlib=xsmp)
        self.requires("libice/1.1.2")             # ice >= 1.0 (--with-sessionlib=xsmp)
        self.requires("alsa-lib/1.2.16")          # alsa >= 1.0 (--with-alsa)
        self.requires("gnutls/3.8.10")            # gnutls >= 3.6.7 (--with-tls=gnutls)
        self.requires("libxcrypt/4.5.2")          # AC_CHECK_LIB(crypt, crypt_r)
        self.requires("zlib/1.3.1.1")             # AC_CHECK_HEADERS(zlib.h) / AC_CHECK_LIB(z, inflate); glib pins 1.3.1.1
        self.requires("cmigemo/1.2-gh0.20220623")  # AC_CHECK_HEADERS(migemo.h) (--with-migemo)

    def build_requirements(self):
        # Tag archive has no configure/aclocal.m4 -> autoreconf bootstrap.
        # CI workers have no automake/libtoolize on PATH.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # AX_CXX_COMPILE_STDCXX([17], [noext], [mandatory]) m4 macro.
        self.tool_requires("autoconf-archive/2024.10.16")
        # GoogleTest backs `make check` only; test_requires stays out of the
        # consumer closure (host context, test=True).
        self.test_requires("gtest/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── generate ────────────────────────────────────────────────────────────

    def _working_shell(self):
        """Return a shell whose getcwd() works inside the HMDFS build tree.

        The ohos-aarch64 profile pins SHELL/CONFIG_SHELL to
        /data/service/hnp/bin/bash; autoconf re-executes itself through
        $CONFIG_SHELL and dies with "working directory cannot be determined"
        when that shell cannot getcwd() in the build tree (E386 family).
        Probe by actually running `pwd` in the build folder — os.access(X_OK)
        is meaningless on HMDFS (E524).
        """
        build_dir = self.build_folder
        os.makedirs(build_dir, exist_ok=True)
        candidates = [shutil.which("bash"),
                      os.path.expanduser("~/.harmonybrew/bin/bash"),
                      "/data/service/hnp/bin/bash",
                      "/bin/sh"]
        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                continue
            try:
                probe = subprocess.run([cand, "-c", "pwd"], cwd=build_dir,
                                       capture_output=True, timeout=30)
            except Exception as exc:  # noqa: BLE001 - probe only
                self.output.info("shell probe %s raised %s" % (cand, exc))
                continue
            if probe.returncode == 0 and b"Not supported" not in probe.stderr:
                self.output.info("using getcwd-capable shell: %s" % cand)
                return cand
            self.output.info("shell candidate rejected: %s (rc=%s err=%r)"
                             % (cand, probe.returncode, probe.stderr[:80]))
        self.output.warning("no getcwd-capable shell found; keeping the profile SHELL")
        return None

    def _validate_pc_paths(self, paths):
        missing = [name for name in REQUIRED_PC
                   if not any(os.path.isfile(os.path.join(p, name + ".pc"))
                              for p in paths)]
        if missing:
            raise ConanException(
                "configure's PKG_CHECK_MODULES would fail: no .pc file for %s "
                "(searched %d pkgconfig dirs: %s)"
                % (", ".join(missing), len(paths), ":".join(paths)))

    def _write_pc_shims(self, paths):
        """Write a pkg-config file for any required package whose .pc is not
        reachable through PKG_CONFIG_PATH.

        Two observed gaps in ohpcd's published packages:
          * gtest/1.17.0 exposes only a `gtest` component in cpp_info, while
            jdim's test/Makefile.am asks pkg-config for `gtest_main >= 1.10.0`;
            upstream googletest does install gtest_main.pc next to
            libgtest_main.a, so this shim is only a fallback.
          * gnutls/3.8.10 ships lib/gnutls.pc (not lib/pkgconfig/gnutls.pc) and
            that file's `prefix=` is the build machine's install prefix, so it
            is neither found nor usable as-is.
        Each shim points at the owning package folder, which is immutable inside
        the Conan cache.
        """
        wanted = {
            "gtest_main": {"dep": "gtest", "libs": "-lgtest_main -lgtest",
                           "desc": "GoogleTest (with main() function)"},
            "gnutls": {"dep": "gnutls", "libs": "-lgnutls",
                       "desc": "Transport Security Layer implementation for the GNU system"},
        }
        for name, spec in wanted.items():
            if any(os.path.isfile(os.path.join(p, name + ".pc")) for p in paths):
                self.output.info("%s.pc provided by the dependency tree" % name)
                continue
            dep = self.dependencies[spec["dep"]]
            pkg = dep.package_folder
            libdir = os.path.join(pkg, "lib")
            incdir = os.path.join(pkg, "include")
            libname = spec["libs"].split()[-1][2:]
            if not any(f == "lib%s.a" % libname or f.startswith("lib%s.so" % libname)
                       for f in os.listdir(libdir)):
                raise ConanException(
                    "%s: no lib%s in %s (needed by jdim's configure.ac)"
                    % (name, libname, libdir))
            text = (
                "prefix={pkg}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir={libdir}\n"
                "includedir={incdir}\n"
                "\n"
                "Name: {name}\n"
                "Description: {desc} (shim written by the jdim recipe)\n"
                "Version: {ver}\n"
                "Libs: -L${{libdir}} {libs}\n"
                "Cflags: -I${{includedir}}\n"
            ).format(pkg=pkg, libdir=libdir, incdir=incdir, name=name,
                     desc=spec["desc"], ver=str(dep.ref.version), libs=spec["libs"])
            dst = os.path.join(self.generators_folder, name + ".pc")
            save(self, dst, text)
            self.output.info("wrote %s (from %s)" % (dst, pkg))

    def _aclocal_dirs(self):
        """ACLOCAL_PATH content: the m4 dirs shipped by the autotools tool
        packages.

        autoconf-archive/2024.10.16 declares ACLOCAL_PATH with
        buildenv_info.define_path(), which *replaces* the value libtool/2.5.4
        contributes with append_path().  The observed result was an
        aclocal.m4 without libtool.m4 -> automake does not recognise LT_INIT
        and aborts every noinst_LIBRARIES with
        "library used but 'RANLIB' is undefined".  Collect all three dirs
        explicitly and hand them to autoreconf with -I as well, so the fix does
        not depend on the env merge order.
        """
        dirs = []
        for dep in self.dependencies.values():
            if dep.ref.name not in ("libtool", "automake", "autoconf-archive"):
                continue
            if not dep.package_folder:
                continue
            candidate = os.path.join(dep.package_folder, "share", "aclocal")
            if os.path.isdir(candidate) and candidate not in dirs:
                dirs.append(candidate)
        return dirs

    def _fix_dependency_components(self):
        """Make gtkmm's cross-package component reference resolvable.

        gtkmm/3.24.11 declares
        components["gtkmm-3.0"].requires = [..., "atkmm::atkmm-1.6", ...]
        but ohpcd's atkmm/2.28.4 exposes a root-level cpp_info with
        pkg_config_name=atkmm-1.6 and no components, so PkgConfigDeps raises
        "Component 'atkmm::atkmm-1.6' not found in 'atkmm' package
        requirement".  Mirror atkmm's root info as the component it is
        referenced by; the dependency recipes themselves stay untouched.
        """
        for dep in self.dependencies.host.values():
            if dep.ref.name != "atkmm":
                continue
            cpp_info = dep.cpp_info
            if "atkmm-1.6" in cpp_info.components:
                continue
            component = cpp_info.components["atkmm-1.6"]
            component.set_property("pkg_config_name", "atkmm-1.6")
            component.libs = list(cpp_info.libs or ["atkmm-1.6"])
            # Absolute dirs: a freshly created component has no dirs of its
            # own, and a bare relative "lib" leaks into LDFLAGS as a literal
            # "-Llib" (observed: ld.lld "unable to find library -latkmm-1.6").
            pkg = dep.package_folder
            component.libdirs = [
                d if os.path.isabs(d) else os.path.join(pkg, d)
                for d in (cpp_info.libdirs or ["lib"])]
            component.includedirs = [
                d if os.path.isabs(d) else os.path.join(pkg, d)
                for d in (cpp_info.includedirs or ["include"])]
            component.bindirs = [
                d if os.path.isabs(d) else os.path.join(pkg, d)
                for d in (cpp_info.bindirs or [])]
            self.output.info("injected atkmm cpp_info component 'atkmm-1.6' "
                             "(libs=%s libdirs=%s)"
                             % (component.libs, component.libdirs))

    def _dependency_lib_dirs(self):
        """Library dirs of the host dependencies.

        AutotoolsDeps puts the dependency libs on every link line (LIBS), so
        both configure's probes and the `make check` test programs need the
        shared gtk stack to be loadable at run time; Conan only exports the
        profile's LD_LIBRARY_PATH (the SDK llvm lib) into conanbuild.
        """
        dirs = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for relative in (("lib",), ("lib64",)):
                candidate = os.path.join(dep.package_folder, *relative)
                if os.path.isdir(candidate) and candidate not in dirs:
                    dirs.append(candidate)
        return dirs

    def _pkg_m4_dirs(self):
        """aclocal dirs that carry pkg-config's pkg.m4.

        PKG_CHECK_MODULES is an m4 macro shipped with pkg-config, which lives
        in the SDK prefix and is *not* part of the Conan tool graph; without
        pkg.m4 aclocal cannot expand it and the generated configure dies with
        `syntax error near unexpected token 'GTKMM,'` (适配检查清单
        Autotools #5).  Locate it from the pkg-config binary instead of
        hardcoding a path (R33).
        """
        candidates = []
        for tool in ("pkg-config", "pkgconf"):
            path = shutil.which(tool)
            if not path:
                continue
            prefix = os.path.dirname(os.path.dirname(os.path.realpath(path)))
            candidates.append(os.path.join(prefix, "share", "aclocal"))
            candidates.extend(glob.glob(os.path.join(
                prefix, "pkg-config.org", "*", "share", "aclocal")))
            candidates.extend(glob.glob(os.path.join(
                prefix, "*", "share", "aclocal")))
        dirs = []
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "pkg.m4")) and candidate not in dirs:
                dirs.append(candidate)
        return dirs

    def _gdk_pixbuf_csource_cmd(self):
        """Self-contained command for the icons rule.

        The tool must also *load* libgdk_pixbuf-2.0/libglib at run time, and
        LD_LIBRARY_PATH from buildenv_info does not reach Autotools.make's
        shell either (same override as PATH).  Prefixing the command with an
        explicit LD_LIBRARY_PATH keeps the rule independent of any env merge
        order.
        """
        libdirs = self._dependency_lib_dirs()
        return 'env LD_LIBRARY_PATH="%s" %s' % (
            ":".join(libdirs), self._gdk_pixbuf_csource())

    def _m4_dirs(self):
        dirs = list(self._aclocal_dirs())
        for candidate in self._pkg_m4_dirs():
            if candidate not in dirs:
                dirs.append(candidate)
        return dirs

    def _sub_tool_path(self, target, tool_name, replacement):
        """Idempotently replace a hardcoded tool name with a self-contained command.

        The generated Makefile inherits the replacement from the patched
        Makefile.am, so a blind second replace would rewrite the replacement
        into itself (observed: "<bin>/<bin>/gdk-pixbuf-csource" -> 127).
        Guard on the replacement's marker instead of on the tool path.
        """
        if not os.path.isfile(target):
            return
        marker = 'LD_LIBRARY_PATH="'
        with open(target, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if marker in text:
            self.output.info("%s: %s already wrapped" %
                             (os.path.basename(target), tool_name))
            return
        replace_in_file(self, target, tool_name, replacement, strict=False)
        self.output.info("%s: %s -> env LD_LIBRARY_PATH=<deps> %s" %
                         (os.path.basename(target), tool_name, replacement.split()[-1]))

    def _deps_lib_shim(self):
        """Per-dependency lib dirs whose *only* difference is the absence of .la.

        The published autotools-built packages ship libtool .la files whose
        ``dependency_libs`` bake the builder's absolute paths, e.g. libX11.la
        references /.../.conan2/p/b/libxcb.../p/lib/libxcb.la (a *build* dir of
        the machine that produced the package).  libtool prefers a .la over the
        .so in the same -L directory, so linking jdim dies with
        ``cannot find the library .../libxcb.la``.  Mirroring each package's
        shared/static libs into a .la-free directory (same basenames, symlinked)
        and pointing that dependency's libdirs there makes libtool link the
        real .so, independent of -L ordering.
        """
        root = os.path.join(self.build_folder, "deplibs")
        os.makedirs(root, exist_ok=True)
        shims = {}
        linked = 0
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder or "", "lib")
            if not os.path.isdir(libdir):
                continue
            shim = os.path.join(root, str(dep.ref.name).replace("/", "_"))
            os.makedirs(shim, exist_ok=True)
            for entry in sorted(os.listdir(libdir)):
                path = os.path.join(libdir, entry)
                if not os.path.isfile(path):
                    continue
                if ".la" in entry or ".py" in entry:
                    continue
                if not (".so" in entry or entry.endswith(".a")):
                    continue
                dst = os.path.join(shim, entry)
                if os.path.exists(dst) or os.path.islink(dst):
                    continue
                try:
                    os.symlink(path, dst)
                    linked += 1
                except OSError:
                    pass
            shims[str(dep.ref.name)] = shim
        self.output.info("deplibs shim: %d libs in %d dirs (%s)"
                         % (linked, len(shims), root))
        return shims

    def _point_libdirs_at_shims(self, shims):
        for dep in self.dependencies.host.values():
            shim = shims.get(str(dep.ref.name))
            if not shim:
                continue
            dep.cpp_info.libdirs = [shim]
            for component in dep.cpp_info.components.values():
                component.libdirs = [shim]

    def _gdk_pixbuf_csource(self):
        """Absolute path of gdk-pixbuf-csource from the dependency package.

        ``src/icons/Makefile.am:28`` hardcodes the tool name (no variable to
        override) and turns the PNG icons into C headers.  The binary ships in
        the gdk-pixbuf package's bin/ dir, which is NOT on PATH in the build
        env: the ohos-aarch64 profile assigns PATH in [buildenv] with plain
        assignment semantics, so a buildenv_info append is replaced (verified
        by reading the generated conanbuildenv-*.sh), and an
        Environment().vars().apply() wrapper is undone again when
        ``Autotools.make`` re-sources conanbuild.sh.  Hence the deterministic
        fix: substitute the absolute path into the Makefile (the recipe does
        not change any upstream semantics, only the tool invocation path).
        """
        for dep in self.dependencies.host.values():
            if dep.ref.name != "gdk-pixbuf" or not dep.package_folder:
                continue
            candidate = os.path.join(dep.package_folder, "bin", "gdk-pixbuf-csource")
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "gdk-pixbuf-csource not found in the gdk-pixbuf dependency package; "
            "src/icons/Makefile.am needs it to generate the icon headers")

    def _configure_args(self, pc_paths):
        return [
            # config.guess on this device fails outright ("can't create
            # ./cgXXXXXX/dummy.c: Permission denied", the HMDFS E011 family),
            # so both triplets are passed explicitly (E566 /
            # 适配检查清单 Autotools #4).  --host linux-ohos also puts
            # configure into cross mode, which is what we want: otherwise every
            # AC_RUN_IFELSE probe compiles a conftest linked against the whole
            # shared gtk stack through AutotoolsDeps' LIBS and then fails to
            # load it ("Error loading shared library libgtkmm-3.0.so.1"), and
            # configure aborts with "cannot run C compiled programs".
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--with-sessionlib=xsmp",
            "--with-tls=gnutls",
            "--with-migemo",
            "--with-alsa",
            # conan does not export PKG_CONFIG_PATH into the conanbuild env;
            # hand it to configure as a command-line variable assignment
            # (abiword-plugin-docbook/3.0.8 pattern).
            "PKG_CONFIG_PATH={}".format(":".join(pc_paths)),
        ]

    def generate(self):
        os.makedirs(os.path.expanduser("~/tmp"), exist_ok=True)
        self.buildenv.define("TMPDIR", os.path.expanduser("~/tmp"))
        shell = self._working_shell()
        if shell:
            self.buildenv.define("SHELL", shell)
            self.buildenv.define("CONFIG_SHELL", shell)

        # PkgConfigDeps writes one flat .pc per graph node and only references
        # packages that are in the graph, so pkg-config never chases a
        # Requires.private entry published by a dependency's build machine
        # (e.g. harfbuzz.pc asking for graphite2 while the graph does not
        # ship it).  Using the dependency packages' own .pc trees instead
        # fails exactly there.
        self._fix_dependency_components()
        shims = self._deps_lib_shim()
        self._point_libdirs_at_shims(shims)
        PkgConfigDeps(self).generate()
        pc_paths = [self.generators_folder]
        self._write_pc_shims(pc_paths)
        self._validate_pc_paths(pc_paths)
        self.output.info("PkgConfigDeps generated .pc files: %d"
                         % len([f for f in os.listdir(self.generators_folder)
                                if f.endswith(".pc")]))

        lib_dirs = self._dependency_lib_dirs()
        for libdir in lib_dirs:
            self.buildenv_info.append_path("LD_LIBRARY_PATH", libdir)
        self.output.info("LD_LIBRARY_PATH += %d dependency libdirs" % len(lib_dirs))

        aclocal_dirs = self._m4_dirs()
        if aclocal_dirs:
            self.buildenv_info.define_path("ACLOCAL_PATH", ":".join(aclocal_dirs))
            for adir in aclocal_dirs:
                self.output.info("ACLOCAL_PATH += %s" % adir)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args(pc_paths))
        tc.generate()
        AutotoolsDeps(self).generate()

    # ── build ───────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        autotools = Autotools(self)
        # 1) bootstrap: tag archive has configure.ac but no configure.
        #    -I keeps aclocal independent of the ACLOCAL_PATH merge (see
        #    _aclocal_dirs): without libtool.m4 in aclocal.m4 automake fails
        #    with "library used but 'RANLIB' is undefined".
        #    src/icons/Makefile.am invokes gdk-pixbuf-csource by bare name;
        #    substitute the absolute path before automake expands it (the
        #    generated Makefile is patched again below).
        self._sub_tool_path(os.path.join(src, "src", "icons", "Makefile.am"),
                            "gdk-pixbuf-csource", self._gdk_pixbuf_csource_cmd())
        autoreconf_args = ["-fi"]
        for adir in self._m4_dirs():
            autoreconf_args += ["-I", adir]
        autotools.autoreconf(args=autoreconf_args)

        # 2) E011/E114: config.status mkdtemp under umask 077 -> drwx--S--- on
        #    HMDFS, which config.status then cannot write into.
        configure = os.path.join(src, "configure")
        with open(configure, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "umask 077" in content:
            with open(configure, "w", encoding="utf-8") as fh:
                fh.write(content.replace("umask 077", "umask 022"))
            self.output.info("configure: umask 077 -> umask 022 (E011/E114)")

        autotools.configure()

        # 3) gdk-pixbuf-csource: absolute path in both the .am (already
        #    re-expanded by autoreconf above) and the generated Makefile.
        for target in (os.path.join(src, "src", "icons", "Makefile.am"),
                       os.path.join(self.build_folder, "src", "icons", "Makefile")):
            self._sub_tool_path(target, "gdk-pixbuf-csource",
                                self._gdk_pixbuf_csource_cmd())

        autotools.make()
        self._run_upstream_tests(src)

    def _read_text(self, path):
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()

    @staticmethod
    def _parse_gtest_summary(text):
        run = re.search(
            r"\[==========\] Running (\d+) tests? from (\d+) test suites?\.", text)
        ok = re.search(r"\[  PASSED  \] (\d+) tests?\.", text)
        bad = re.search(r"\[  FAILED  \] (\d+) tests?", text)
        skip = re.search(r"\[  SKIPPED \] (\d+) tests?", text)
        return {
            "cases": int(run.group(1)) if run else None,
            "suites": int(run.group(2)) if run else None,
            "passed": int(ok.group(1)) if ok else 0,
            "failed": int(bad.group(1)) if bad else 0,
            "skipped": int(skip.group(1)) if skip else 0,
        }

    @staticmethod
    def _parse_automake_summary(text):
        m = re.search(
            r"# TOTAL:\s+(\d+)\s*\n# PASS:\s+(\d+)\s*\n# SKIP:\s+(\d+)\s*\n"
            r"# XFAIL:\s+(\d+)\s*\n# FAIL:\s+(\d+)\s*\n# XPASS:\s+(\d+)\s*\n"
            r"# ERROR:\s+(\d+)", text)
        if m:
            return {"total": int(m.group(1)), "pass": int(m.group(2)),
                    "skip": int(m.group(3)), "xfail": int(m.group(4)),
                    "fail": int(m.group(5)) + int(m.group(7)),
                    "xpass": int(m.group(6)), "error": int(m.group(7))}
        m_all = re.search(r"^All (\d+) tests passed\s*$", text, re.M)
        if m_all:
            n = int(m_all.group(1))
            return {"total": n, "pass": n, "skip": 0, "fail": 0, "error": 0}
        m_fail = re.search(r"^(\d+) of (\d+) tests failed\s*$", text, re.M)
        if m_fail:
            total = int(m_fail.group(2))
            failed = int(m_fail.group(1))
            return {"total": total, "pass": total - failed, "skip": 0,
                    "fail": failed, "error": 0}
        return {}

    def _run_upstream_tests(self, src):
        """Run the upstream gtest suite for real and record the case ledger.

        Two environment facts drive this implementation:
          * the tree is built out-of-source, so the `check` target and the
            check_PROGRAMS live in the build folder (`make check` in the source
            folder fails with "No rule to make target 'check'");
          * the profile's [buildenv] PATH/LD_LIBRARY_PATH assignments override
            whatever buildenv_info adds, so the test binary would not find the
            shared gtk stack -- the library search path is therefore put on the
            command line itself.
        Four cases are a documented platform baseline: upstream expects jdim's
        numeric-character-reference fallback for unrepresentable characters,
        but on this libc iconv("ASCII", "UTF-8") substitutes '*' instead of
        failing (verified with a standalone iconv probe), so the fallback is
        never taken.  Any other failure, or a drop below the pass baseline,
        fails the build.
        """
        build = self.build_folder
        test_dir = os.path.join(build, "test")
        check_log = os.path.join(build, "make-check.log")
        libpath = ":".join(self._dependency_lib_dirs())
        check_rc = 0
        try:
            self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
                     'make check > "%s" 2>&1' % (libpath, check_log),
                     env="conanbuild", cwd=build)
        except ConanException:
            check_rc = 1

        harness = self._read_text(check_log)
        detail = self._read_text(os.path.join(test_dir, "test-suite.log"))
        detail += "\n" + self._read_text(os.path.join(test_dir, "gtest_jdim.log"))
        if not detail.strip():
            detail = harness

        gtest = self._parse_gtest_summary(detail)
        automake = self._parse_automake_summary(harness + "\n" + detail)
        failed_names = []
        for line in detail.splitlines():
            match = re.match(r"\[  FAILED  \] ([^0-9].*?) \(", line)
            if match:
                name = match.group(1).strip()
                if name and name not in failed_names:
                    failed_names.append(name)

        if not gtest.get("cases"):
            tail = "\n".join((detail or harness).splitlines()[-25:])
            raise ConanException(
                "make check ran but no gtest summary was found -- the upstream "
                "suite did not execute.\nmake check rc=%s\nlog tail:\n%s"
                % (check_rc, tail))

        if gtest["cases"] != UPSTREAM_REGISTERED_CASES:
            raise ConanException(
                "gtest registered %d atomic cases, expected %d of %d static "
                "declarations (test sources silently dropped?)"
                % (gtest["cases"], UPSTREAM_REGISTERED_CASES, UPSTREAM_TEST_CASES))

        unexpected = [n for n in failed_names if n not in KNOWN_PLATFORM_FAILURES]
        if unexpected or gtest["passed"] < UPSTREAM_PASS_BASELINE:
            raise ConanInvalidConfiguration(
                "jdim upstream gtest suite regressed: %d passed (baseline %d), "
                "%d failed, unexpected: %s (make check rc=%s)\n%s"
                % (gtest["passed"], UPSTREAM_PASS_BASELINE, gtest["failed"],
                   unexpected, check_rc,
                   "\n".join(ln for ln in detail.splitlines()
                              if ln.startswith("[  FAILED  ]"))[:4000]))

        evidence = [ln for ln in (detail + "\n" + harness).splitlines()
                    if ln.startswith("[==========]")
                    or ln.startswith("[  PASSED  ]")
                    or ln.startswith("[  SKIPPED ]")
                    or ln.startswith("[  FAILED  ]")
                    or ln.startswith("PASS:")
                    or ln.startswith("FAIL:")
                    or ln.startswith("# TOTAL:")
                    or ln.startswith("# PASS:")
                    or ln.startswith("# FAIL:")]
        result = {
            "software": self.name,
            "version": self.version,
            "test_program": "test/gtest_jdim",
            "upstream_gtest_sources": UPSTREAM_GTEST_SOURCES,
            "static_cases": UPSTREAM_TEST_CASES,
            "registered_cases": UPSTREAM_REGISTERED_CASES,
            "executed_cases": gtest["cases"],
            "suites": gtest["suites"],
            "passed": gtest["passed"],
            "failed": gtest["failed"],
            "skipped": gtest["skipped"],
            "pass_baseline": UPSTREAM_PASS_BASELINE,
            "known_platform_failures": list(KNOWN_PLATFORM_FAILURES),
            "failed_cases": failed_names,
            "not_registered_reason": {
                "cases": UPSTREAM_TEST_CASES - UPSTREAM_REGISTERED_CASES,
                "reason": "inside #ifdef _POSIX_C_SOURCE in "
                          "test/gtest_jdlib_misctime.cpp (macro not defined)",
            },
            "platform_failure_reason":
                "libc charset capability wall: (a) 2 x MISC_UrlEncode*Test."
                "encoded_to_eucjp fail on \"can't open iconv coding = UTF-8 to "
                "EUCJP-MS\" (EUCJP-MS charset absent in this libc); (b) 2 x "
                "Iconv_ToAsciiFromUtf8.* get '*' substitution from "
                "iconv(ASCII, UTF-8) instead of EILSEQ (ASCII//TRANSLIT also "
                "unavailable), so jdim's numeric character reference fallback "
                "is never taken",
            "automake_harness": automake,
            "make_check_rc": check_rc,
            "consumer_programs": 1,
            "evidence_lines": evidence,
        }
        save(self, os.path.join(self.build_folder, "upstream_test_result.json"),
             json.dumps(result, ensure_ascii=False, indent=2))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False),
              flush=True)
    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
