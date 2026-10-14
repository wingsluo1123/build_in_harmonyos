#!/usr/bin/env python3
"""Conan recipe — snort 3.12.2.0 (OpenHarmony PC adaptation).

Snort 3 is a network intrusion detection / prevention system (NIDS/NIPS).
Upstream builds with CMake through the `configure_cmake.sh` wrapper; this
recipe invokes CMake directly with the same cache entries so the build stays
fully visible to the Conan toolchain.

Required upstream dependencies (cmake/include_libraries.cmake): Threads,
DAQ (libdaq >= 3.0.27), dnet, FlexLexer (flex >= 2.6.0), hwloc, LuaJIT,
OpenSSL >= 1.1.1, libpcap, pcre2, zlib.  The unit test suite additionally
needs CppUTest.  Optional libraries (hyperscan, safec, ...) are found QUIET
and are intentionally left absent here; lzma is required in this recipe
(liblzma/5.8.1) and enabled via the LIBLZMA_FOUND gate of patch 0001.

Notes
- libdaq 3.0.27 has no release tarball and is not packaged in the OpenHarmony
  Conan repo, so it is vendored as a second source and its build system is
  re-generated step by step (libtoolize / aclocal / autoheader / automake /
  autoconf).  `autoreconf` cannot be used on the OHOS device: execve of
  script files on the HMDFS home filesystem fails with EACCES, so the conan
  autoconf/automake wrapper scripts are never launchable there; automake and
  libtool come from tool_requires and are driven through `perl`/`sh`, while
  autoconf and autoheader are native host binaries.  It is configured
  --disable-shared so
  nothing depends on .so symlinks (not supported on the OHOS device file
  system).  Upstream installs the generated `libdaq_static_*.pc` files only
  for shared-module builds, but snort's FindDAQ discovers the static modules
  through `pkg-config --list-all`; the recipe therefore copies those .pc files
  into the vendor prefix after `make install`.
- ENABLE_UNIT_TESTS=ON is kept ON in the shipped package: the `snort` binary
  then embeds the Catch2 suite (`snort --catch-test all`), and the CppUTest
  executables are built and exercised through CTest (`make check`).
- Patch 0001 also routes snort's build-time helper scripts (lua_wrap.sh,
  ffi_wrap.sh, plug_gen.sh) through `sh`: HMDFS denies execve of script
  files even when the executable bit is set, so the generated headers can
  only be produced by handing the scripts to an interpreter.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMakeToolchain
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load, save)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SnortConan(ConanFile):
    name = "snort"
    version = "3.12.2.0"
    description = ("Snort 3 — lightweight network intrusion detection and "
                   "prevention system (NIDS/NIPS)")
    license = "GPL-2.0-only"
    homepage = "https://www.snort.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # REQUIRED by snort's CMake configure step
        self.requires("libpcap/1.10.6")                   # packet capture
        self.requires("pcre2/10.45")                      # regex engine
        self.requires("hwloc/2.14.0")                     # thread affinity
        self.requires("libdnet/1.12")                     # network addresses
        self.requires("openssl/3.5.6.1")                  # hashes / TLS
        self.requires("zlib/1.3.1.1")                     # compressed rules
        self.requires("luajit-openresty/2.1-20260311.1")  # config + rule engine
        self.requires("cpputest/4.0_r2")                  # unit tests
        # optional upstream library that ships in the OHOS registry
        self.requires("liblzma/5.8.1")                    # lzma file/rule decompression

    def build_requirements(self):
        self.tool_requires("flex/2.6.4.2")     # lexer generator + FlexLexer.h
        self.tool_requires("pkgconf/3.0.5")    # FindDAQ/FindHWLOC/CppUTest
        # libdaq bootstrap: automake/libtool come from the repo (workers may
        # lack them); autoconf/autoheader are taken from the host toolchain
        # (hnp) — the conan autoconf wrappers are script shells that cannot
        # be execve'd on the HMDFS device filesystem.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["libdaq"], destination="libdaq-src",
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The device CMake auto-detects the host system as "HarmonyOS", for
        # which it ships no platform module: none of the ELF runtime-path
        # flag definitions (-Wl,-rpath, / -Wl,-rpath-link,) exist there
        # (probed: every CMAKE_*_RUNTIME_*_FLAG variable is empty), so CMake
        # silently drops rpath flags no matter what CMAKE_INSTALL_RPATH
        # says.  The same CMake ships Platform/OHOS.cmake (= include
        # (Platform/Linux)) for the intended system name; pinning it was
        # validated to yield the full flag set (mini-project RUNPATH probe).
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # The application lives in bin/ while the one shared dependency
        # (hwloc) lives in its own package folder: with no rpath at all the
        # official L2 smoke gate cannot even start bin/snort with an empty
        # environment, and the in-build ctest executables link the same
        # libraries.  "$ORIGIN/../lib" covers this package's own libs, every
        # dependency lib dir is appended verbatim (accessibility 26.04.3
        # precedent).
        rpath_dirs = ["$ORIGIN/../lib"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    rpath_dirs.append(lib_dir)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(rpath_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)
        # CMake normally links with a build-tree rpath and *rewrites* the
        # installed ELF's rpath in place.  On OHOS every ELF carries a
        # .codesign section written at link time and any post-link rewrite
        # invalidates it - the installed binary then refuses to exec with
        # "Operation not permitted" (known class: strip/rpath rewrite vs
        # codesign, DRAFT-E703).  Linking with the final install rpath from
        # the start makes the install step a byte-identical copy, keeping
        # the signature valid, so bin/snort runs both plain and with an
        # empty environment.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        tc.generate()

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _dep_dir(dep, attr, fallback):
        dirs = getattr(dep.cpp_info, attr)
        if dirs and dirs[0]:
            return os.path.join(dep.package_folder, dirs[0])
        return os.path.join(dep.package_folder, fallback)

    @staticmethod
    def _sdk_llvm_lib_dirs():
        """SDK llvm/lib dirs that hold lld's runtime deps (libxml2.so.16).

        2026-10-13 analysis: the CI workers' opaque `checking whether the C
        compiler works... no` wall (26 fails / 15 workers, never past libdaq)
        matches the platform profile note "worker 上缺失时所有链接步骤报
        Error loading shared library libxml2.so.16"; our device links even
        under `env -i` (a loader fallback the workers lack).  So do not rely
        on the profile alone: locate the real SDK install ourselves.
        """
        base = "/data/service/hnp/ohos-sdk.org"
        try:
            names = sorted(os.listdir(base), reverse=True)
        except OSError:
            return []
        found = []
        for name in names:
            if not name.startswith("ohos-sdk_"):
                continue
            d = os.path.join(base, name, "ohos", "native", "llvm", "lib")
            if os.path.isdir(d) and (os.path.exists(os.path.join(d, "libxml2.so.16"))
                                     or os.path.exists(os.path.join(d, "lld"))):
                found.append(d)
        return found

    @classmethod
    def _env_prefix(cls, tmpdir, pkg_dirs, path_extra, lib_dirs):
        parts = []
        if path_extra:
            # $PATH is expanded after conanbuild.sh has run, so the profile
            # [buildenv] entries (hnp clang/bash) and tool_require bindirs
            # stay visible; ours are merely prepended.
            parts.append('PATH="%s:$PATH"' % ":".join(path_extra))
        if pkg_dirs:
            parts.append('PKG_CONFIG_PATH="%s"' % ":".join(pkg_dirs))
        # keep the profile-provided LD_LIBRARY_PATH: the OHOS lld needs
        # llvm/lib on it to resolve libxml2.so.16 while linking -- and the
        # SDK dir goes in explicitly, in case the profile's [buildenv] did
        # not reach this process on a given worker image.
        lib_dirs = cls._sdk_llvm_lib_dirs() + list(lib_dirs)
        if lib_dirs:
            parts.append('LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"'
                         % ":".join(lib_dirs))
        # the profile [buildenv] also hands autoconf a bash CONFIG_SHELL --
        # same belt-and-braces: profiles have silently lost entries before
        # (upstream 173de581e5) and no CI log proves they reach self.run().
        hnp_bash = "/data/service/hnp/bin/bash"
        if os.path.exists(hnp_bash):
            parts.append('CONFIG_SHELL="%s" SHELL="%s"' % (hnp_bash, hnp_bash))
        # OHOS /tmp is read-only; keep build temporaries inside the build dir
        parts.append('TMPDIR="%s"' % tmpdir)
        return " ".join(parts)

    # ------------------------------------------------- libdaq bootstrap
    def _bootstrap_libdaq(self, env, daq_src, tools):
        """Hand-rolled `autoreconf -ivf` for the vendored libdaq.

        On the OHOS device, execve of script files on the HMDFS home
        filesystem fails with EACCES, so conan's autoconf/automake wrapper
        scripts can never be launched directly; every step is driven through
        `sh`, `perl` or a native host binary instead.  libtoolize runs before
        aclocal so that the m4 / time-stamp chain aclocal.m4 -> config.h.in /
        Makefile.in -> configure -> Makefile stays clean and make never tries
        to re-run a tool.
        """
        am_pkg = tools["automake"].package_folder
        am_bin = os.path.join(am_pkg, "bin")
        lt_pkg = tools["libtool"].package_folder
        py_pkg = tools["pkgconf"].package_folder

        # libtoolize wants $pkgdatadir/{build-aux,libltdl,m4}; the shipped
        # share/libtool-conan directory is empty (it held symlinks only).
        lt_data = os.path.join(self.build_folder, "lt-pkgdata")
        shutil.rmtree(lt_data, ignore_errors=True)
        for sub, src in (("build-aux", os.path.join(lt_pkg, "share", "libtool",
                                                    "build-aux")),
                         ("libltdl", os.path.join(lt_pkg, "share", "libtool",
                                                  "libltdl")),
                         ("m4", os.path.join(lt_pkg, "share", "aclocal"))):
            shutil.copytree(src, os.path.join(lt_data, sub))

        m4_inc = ":".join((os.path.join(daq_src, "m4"),
                           os.path.join(lt_pkg, "share", "aclocal"),
                           os.path.join(py_pkg, "share", "aclocal")))
        steps = (
            ("libtoolize",
             '_lt_pkgdatadir="%s" sh "%s/bin/libtoolize" --force -c'
             % (lt_data, lt_pkg)),
            ("aclocal",
             'ACLOCAL_PATH="%s:$ACLOCAL_PATH" perl "%s/.aclocal-real" '
             '--automake-acdir="%s/share/aclocal-1.18" '
             '--system-acdir="%s/share/aclocal" --force'
             % (m4_inc, am_bin, am_pkg, am_pkg)),
            ("autoheader", "autoheader"),
            ("automake",
             'perl "%s/.automake-real" --libdir="%s/share/automake-1.18" '
             '--add-missing -c --foreign' % (am_bin, am_pkg)),
            ("autoconf", "autoconf"),
        )
        boot_env = ('%s PERL5LIB="%s/share/automake-1.18:$PERL5LIB"'
                    % (env, am_pkg))
        for name, cmd in steps:
            self.output.info("  bootstrap: %s" % name)
            self.run(f"{boot_env} {cmd}", cwd=daq_src)

        cfg = os.path.join(daq_src, "configure")
        if not os.path.isfile(cfg):
            raise ConanException("bootstrap: autoconf produced no configure")
        # autoconf only warns on undefined macros; an m4 path problem would
        # leave the macro names as shell literals inside configure instead.
        blob = load(self, cfg)
        for token in ("LT_INIT", "PKG_INSTALLDIR"):
            if token in blob:
                raise ConanException(
                    "bootstrap: unexpanded macro %s left in configure "
                    "(m4 include path broken)" % token)

    def _pin_configure_tmpdir(self, env, daq_src, fixed_tmp):
        """E114: HMDFS refuses file writes from script-spawned processes into
        freshly created directories (config.status' AS_TMPDIR ./confXXXXXX,
        clang's TMPDIR scratch files).  Pre-create a directory, export it as
        TMPDIR and point the generated configure's ac_tmp at it; drop the
        cleanup trap so later steps still find the shared directory."""
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp
        cfg = os.path.join(daq_src, "configure")
        blob = load(self, cfg)
        if "ac_tmp=$tmp" not in blob:
            raise ConanException("E114: 'ac_tmp=$tmp' not found in configure")
        blob = blob.replace("ac_tmp=$tmp", 'ac_tmp="%s"' % fixed_tmp)
        trap = ('{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && '
                'exit $exit_status')
        if trap in blob:
            blob = blob.replace(trap, "exit $exit_status")
        if 'rm -fr "$ac_tmp"' in blob:
            raise ConanException("E114: ac_tmp cleanup trap not neutralised")
        save(self, cfg, blob)
        os.chmod(cfg, 0o755)
        self.output.info("  [ok] E114: configure ac_tmp -> %s" % fixed_tmp)

    # ------------------------------------------------------------------ build
    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = comp.get("c") or "clang"
        cxx = comp.get("cpp") or "clang++"
        # tools.build:jobs wins when set; otherwise 8 keeps the 20-core OHOS
        # PC busy without the memory spikes -j20 would cause for this tree.
        jobs = self.conf.get("tools.build:jobs", default=8, check_type=int) or 8

        host_deps = [d for d in self.dependencies.values() if d.package_folder]
        build_deps = [d for d in self.dependencies.build.values()
                      if d.package_folder]
        deps = {str(d.ref.name): d for d in host_deps}
        tools = {str(d.ref.name): d for d in build_deps}

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # tool binaries (flex, pkgconf, autoconf/automake/libtool, m4, ...)
        tool_bins = []
        for d in build_deps:
            for sub in d.cpp_info.bindirs:
                p = os.path.join(d.package_folder, sub)
                if os.path.isdir(p):
                    tool_bins.append(p)

        # pkg-config search path: vendored libdaq + every host dependency
        pkg_dirs = [os.path.join(self.build_folder, "libdaq-prefix",
                                 "lib", "pkgconfig")]
        lib_dirs = []
        for d in host_deps:
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                p = os.path.join(d.package_folder, sub)
                if os.path.isdir(p):
                    pkg_dirs.append(p)
            for sub in d.cpp_info.libdirs:
                p = os.path.join(d.package_folder, sub)
                if os.path.isdir(p) and p not in lib_dirs:
                    lib_dirs.append(p)

        env = self._env_prefix(tmpdir, pkg_dirs, tool_bins, lib_dirs)

        # ------------------------------------------------ 1) vendored libdaq
        daq_src = os.path.join(self.source_folder, "libdaq-src")
        daq_build = os.path.join(self.build_folder, "libdaq-build")
        daq_prefix = os.path.join(self.build_folder, "libdaq-prefix")
        os.makedirs(daq_build, exist_ok=True)
        os.makedirs(daq_prefix, exist_ok=True)

        pcap_inc = self._dep_dir(deps["libpcap"], "includedirs", "include")
        pcap_lib = self._dep_dir(deps["libpcap"], "libdirs", "lib")

        self.output.info("Building vendored libdaq 3.0.27 (static modules)")
        self._bootstrap_libdaq(env, daq_src, tools)
        self._pin_configure_tmpdir(env, daq_src, tmpdir)
        # 2026-10-13: the first autoconf C-compiler check died with the opaque
        # "C compiler cannot create executables" on every CI worker (26 fails
        # / 15 workers / 0 passes) while the very same recipe is green on the
        # device.  Run the identical probe first with the driver's own stderr
        # in the log, so the failing run names the real culprit (lld unable
        # to load libxml2.so.16, dead linker, wrong loader path, ...).
        with open(os.path.join(daq_build, ".ccprobe.c"), "w") as fh:
            fh.write("int main(void){return 0;}\n")
        self.run(
            f'{env} sh -c \'echo "ccprobe: LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; '
            f'echo "ccprobe: SHELL=$SHELL CONFIG_SHELL=$CONFIG_SHELL TMPDIR=$TMPDIR"; '
            f'cd "{daq_build}"; '
            f'"{cc}" -v .ccprobe.c -o .ccprobe.out > .ccprobe.log 2>&1; '
            f'rc=$?; echo "ccprobe: rc=$rc"; tail -n 60 .ccprobe.log; '
            f'exit $rc\'')
        # configure is a script on HMDFS: it cannot be execve'd directly and
        # must be handed to an interpreter (repo-wide pattern, e.g. abiword).
        try:
            self.run(
                f'{env} sh "{daq_src}/configure" '
                f'--prefix="{daq_prefix}" '
                "--build=aarch64-unknown-linux-ohos "
                "--disable-shared --enable-static "
                "--disable-dependency-tracking "
                f'--with-libpcap-includes="{pcap_inc}" '
                f'--with-libpcap-libraries="{pcap_lib}" '
                f'CPPFLAGS="-I{pcap_inc}" LDFLAGS="-L{pcap_lib}" '
                f'CC="{cc}" CXX="{cxx}"',
                cwd=daq_build)
        except ConanException:
            # autoconf buries the real reason in config.log; surface its tail
            # in the CI log before dying (the worker-side failure has only
            # ever shown the generic "cannot create executables" line).
            self.run(f'{env} sh -c \'tail -n 120 config.log || true\'',
                     cwd=daq_build)
            raise
        make_guard = "ACLOCAL=true AUTOMAKE=true AUTOHEADER=true"
        # HMDFS rejects mkfifo, which GNU make's default FIFO jobserver
        # needs; the pipe jobserver variant is device-proven to run clean.
        self.run(f"{env} make --jobserver-style=pipe -j{jobs} {make_guard}",
                 cwd=daq_build)

        # install-sh is a shell script (cannot be execve'd on HMDFS) and the
        # generated rules run it bare; re-point the two knobs at an `sh`
        # invocation (same workaround as the trousers recipe).
        install_sh = None
        for root, _dirs, names in os.walk(daq_src):
            if "install-sh" in names:
                install_sh = os.path.join(root, "install-sh")
                break
        if not install_sh:
            raise ConanException("libdaq: install-sh not found in source")
        self.run(f"{env} make --jobserver-style=pipe install {make_guard} "
                 f'install_sh="sh {install_sh}" '
                 f'MKDIR_P="sh {install_sh} -c -d"',
                 cwd=daq_build)

        # Upstream installs libdaq_static_*.pc only for shared-module builds;
        # snort's FindDAQ needs them for static module discovery.
        daq_pc_dst = os.path.join(daq_prefix, "lib", "pkgconfig")
        os.makedirs(daq_pc_dst, exist_ok=True)
        for pc in glob.glob(os.path.join(daq_build, "modules", "*",
                                         "libdaq_static_*.pc")):
            copy(self, os.path.basename(pc), os.path.dirname(pc), daq_pc_dst)

        # ------------------------------------------------ 2) snort via CMake
        snort_build = os.path.join(self.build_folder, "snort-build")

        flex_exe = os.path.join(tools["flex"].package_folder, "bin", "flex")
        flex_inc = self._dep_dir(tools["flex"], "includedirs", "include")
        luajit = deps["luajit-openresty"]
        pcre2 = deps["pcre2"]
        dnet = deps["libdnet"]
        cpputest = deps["cpputest"]

        pkgconf_exe = None
        for name in ("pkg-config", "pkgconf"):
            p = os.path.join(tools["pkgconf"].package_folder, "bin", name)
            if os.path.exists(p):
                pkgconf_exe = p
                break

        cmake_vars = [
            ("CMAKE_TOOLCHAIN_FILE",
             os.path.join(self.generators_folder, "conan_toolchain.cmake")),
            ("CMAKE_INSTALL_PREFIX", self.package_folder),
            ("CMAKE_PREFIX_PATH", ";".join(d.package_folder
                                           for d in host_deps)),
            ("ENABLE_UNIT_TESTS", "ON"),
            ("MAKE_DOC", "OFF"),
            ("MAKE_HTML_DOC", "OFF"),
            ("MAKE_PDF_DOC", "OFF"),
            ("MAKE_TEXT_DOC", "OFF"),
            # search hints — equivalents of configure_cmake.sh --with-* flags
            ("PCAP_INCLUDE_DIR_HINT", pcap_inc),
            ("PCAP_LIBRARIES_DIR_HINT", pcap_lib),
            ("LUAJIT_INCLUDE_DIR_HINT",
             self._dep_dir(luajit, "includedirs", "include")),
            ("LUAJIT_LIBRARIES_DIR_HINT",
             self._dep_dir(luajit, "libdirs", "lib")),
            ("LUAJIT_LIBRARY_DIR_HINT",
             self._dep_dir(luajit, "libdirs", "lib")),
            ("PCRE2_INCLUDE_DIR_HINT",
             self._dep_dir(pcre2, "includedirs", "include")),
            ("PCRE2_LIBRARIES_DIR_HINT",
             self._dep_dir(pcre2, "libdirs", "lib")),
            ("DNET_INCLUDE_DIR_HINT",
             self._dep_dir(dnet, "includedirs", "include")),
            ("DNET_LIBRARIES_DIR_HINT",
             self._dep_dir(dnet, "libdirs", "lib")),
            # Conan's toolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG, so
            # find_package(CppUTest) resolves the package's own CppUTestConfig
            # instead of snort's pkg-config-only FindCppUTest.cmake - leaving
            # the uppercase variables macros.cmake consumes unset (test
            # executables then miss CppUTest/CommandLineTestRunner.h and fail
            # to link).  Anchor both directly.
            ("CPPUTEST_INCLUDE_DIR",
             self._dep_dir(cpputest, "includedirs", "include")),
            ("CPPUTEST_LIBRARIES",
             ";".join(os.path.join(self._dep_dir(cpputest, "libdirs", "lib"), n)
                      for n in ("libCppUTest.a", "libCppUTestExt.a"))),
            ("DAQ_INCLUDE_DIR_HINT", os.path.join(daq_prefix, "include")),
            ("DAQ_LIBRARIES_DIR_HINT", os.path.join(daq_prefix, "lib")),
            ("FLEX_INCLUDE_DIR_HINT", flex_inc),
            ("FLEX_EXECUTABLE", flex_exe),
            ("OPENSSL_ROOT_DIR", deps["openssl"].package_folder),
        ]
        if pkgconf_exe:
            cmake_vars.append(("PKG_CONFIG_EXECUTABLE", pkgconf_exe))
        flags = " ".join('-D%s="%s"' % (k, v) for k, v in cmake_vars)

        self.output.info("Configuring snort3 with CMake")
        self.run(f'{env} cmake -G "Unix Makefiles" '
                 f'-S "{self.source_folder}" -B "{snort_build}" {flags}',
                 cwd=self.build_folder)

        self.output.info("Building the snort binary (this takes a while)")
        self.run(f'{env} cmake --build "{snort_build}" --target snort '
                 f'-- -j{jobs} --jobserver-style=pipe', cwd=self.build_folder)

        self.output.info("Building and running the upstream test suites "
                         "(CppUTest executables through CTest)")
        self.run(f'{env} cmake --build "{snort_build}" --target check '
                 f'-- -j{jobs} --jobserver-style=pipe', cwd=self.build_folder)

        # The upstream install rules reference artifacts that only the
        # default (ALL) target produces: the generated api_options.h /
        # snort_api.h headers (install(FILES)), the api_def archive, the
        # daq modules and the four tools (install(TARGETS)); building just
        # `snort` and `check` leaves them absent and `cmake --install`
        # fails on the missing files.  One `all` build also relinks every
        # installed ELF with the install rpath (see generate()), so the
        # install step never rewrites a signed binary.
        self.output.info("Building the remaining install-time targets (ALL)")
        self.run(f'{env} cmake --build "{snort_build}" --target all '
                 f'-- -j{jobs} --jobserver-style=pipe',
                 cwd=self.build_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        snort_build = os.path.join(self.build_folder, "snort-build")
        self.run(f'cmake --install "{snort_build}"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
