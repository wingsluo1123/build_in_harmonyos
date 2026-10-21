#!/usr/bin/env python3
"""Conan recipe for VTR 9.0.0 -- the Verilog-to-Routing FPGA CAD flow.

VTR is not a library: it is a *tool suite plus a flow tree*.  One package ships
the whole CAD chain and the scripts that drive it:

    ODIN II / Yosys+Parmys  -> elaboration + synthesis      (two front ends)
    ABC                     -> logic optimisation + tech mapping
    VPR                     -> packing, placement, routing, timing analysis, power
    ACE 2                   -> clock-network / power estimation
    genfasm, vqm2blif       -> bitstream / netlist writers

WHY THIS RECIPE PACKAGES A TREE AND NOT JUST bin/  (decisive detail)
--------------------------------------------------------------------
`vtr_flow/scripts/python_libs/vtr/paths.py` derives the installation root from
its own location:

    root_path = pathlib.Path(__file__).absolute().parent.parent.parent.parent.parent

and then resolves every tool relative to that root:

    yosys_exe_path = root_path / "build" / "bin" / "yosys"
    abc_exe_path   = root_path / "abc"  / "abc"
    vpr_exe_path   = root_path / "vpr"  / "vpr"
    ace_exe_path   = root_path / "ace2" / "ace"
    odin_exe_path  = root_path / "odin_ii" / "odin_ii"

Upstream satisfies those paths with committed symlinks in the source tree
(`vpr/vpr -> ../build/vpr/vpr`, git mode 120000).  A Conan package that only
kept `cmake.install()`'s `bin/` would leave every one of those paths dangling
and the flow would not start.  So package() reconstructs the layout the flow
actually expects -- flow tree plus tool entry points -- on top of the normal
install rules.

BUILD ENVIRONMENT NOTES
-----------------------
* WITH_PARMYS is ON by default upstream and drives *Yosys's own Makefile*
  (yosys/CMakeLists.txt:18-32 runs `make ENABLE_ABC=0 && make install`).  That
  Makefile, not CMake, discovers Tcl, readline, libffi and zlib -- through
  pkg-config and through CXXFLAGS/LIBS inherited from the environment.  Those
  therefore have to be exported into the build environment here, which is why
  generate() builds an explicit Environment instead of relying on the CMake
  toolchain alone.
* ENABLE_PYOSYS is 0 in yosys/Makefile:31, so the Boost.Python hard error
  (yosys/Makefile:336) is not reachable and Boost is NOT a dependency.
* ABC is built by VTR's CMake, and VTR force-defines READLINE_FOUND FALSE
  (root CMakeLists.txt:385) so ABC does not link readline.
* `VPR_USE_EZGL=off` is upstream's own sanctioned headless configuration -
  root CMakeLists.txt:394-406 auto-detects GTK3+X11 and falls back to
  "VPR Graphics: Disabled", and upstream CI carries a "Basic with NO_GRAPHICS"
  matrix entry using exactly -DVPR_USE_EZGL=off.  Note the upstream coupling at
  vpr/CMakeLists.txt:38-52: with EZGL off, VPR's *server mode* is switched off
  too.  Neither affects synthesis, packing, placement, routing or timing.
"""
import glob
import io
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class VtrConan(ConanFile):
    name = "vtr"
    version = "9.0.0"
    description = ("VTR (Verilog-to-Routing): FPGA CAD flow -- ODIN II/Yosys+Parmys "
                   "elaboration, ABC synthesis, VPR pack/place/route/timing, ACE 2")
    license = "MIT"
    homepage = "https://github.com/verilog-to-routing/vtr-verilog-to-routing"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        # ODIN II is upstream-optional (root CMakeLists.txt:54, default OFF).
        # It is enabled here because it is a first-class elaborator of the VTR 9
        # flow and because the upstream regression tree ships a full `*_odin`
        # suite (vtr_reg_basic_odin, vtr_reg_strong_odin, vtr_reg_nightly*_odin).
        "with_odin": [True, False],
        # Upstream-sanctioned headless build (see module docstring).  Enabling
        # this needs GTK3 + X11 through pkg-config.
        "with_graphics": [True, False],
        "with_capnproto": [True, False],
    }
    default_options = {
        "with_odin": True,
        "with_graphics": False,
        "with_capnproto": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("vtr is supported on Linux/OHOS only")

    def layout(self):
        # cmake_layout puts the build tree at <source>/build, which is exactly
        # where VTR's committed symlinks (abc/abc -> ../build/abc/abc) and
        # paths.py look for the freshly built binaries.
        cmake_layout(self)

    def requirements(self):
        # vpr/CMakeLists.txt:124 + libs/libvtrcapnproto + yosys ENABLE_ZLIB
        self.requires("zlib/1.3.1")
        # libs/EXTERNAL/capnproto/c++/CMakeLists.txt:68  (REQUIRED COMPONENTS Crypto SSL)
        if self.options.with_capnproto:
            self.requires("openssl/3.5.6")
        # vpr/CMakeLists.txt:83 - gates -DEIGEN_INSTALLED and VPR_ANALYTIC_PLACE.
        # Without it upstream silently disables analytic placement.
        self.requires("eigen/3.4.1")
        # Yosys (driven by WITH_PARMYS) with its Makefile defaults:
        #   ENABLE_TCL := 1, ENABLE_READLINE := 1, ENABLE_PLUGINS := 1
        self.requires("tcl/8.6.16")
        self.requires("readline/8.3")
        self.requires("libffi/3.5.2")

    def build_requirements(self):
        # Always required by VTR itself (libvqm, libsdcparse, libblifparse,
        # libtatumparse) and additionally by odin_ii when with_odin is on.
        self.tool_requires("bison/3.8.2")
        # flex/2.6.4 is NOT usable: the OHOS repository's 2.6.4 recipe revision
        # that a worker resolves has no binary at all ("No packages found for
        # this revision"), so a build that must not compile dependencies from
        # source fails with
        #     ERROR: Missing binary: flex/2.6.4:<pkgid>
        # 2.6.4.2 is the revision that actually carries a prebuilt package for
        # the ohos-aarch64 profile (verified for arch=armv8, clang 15, OHOS 6.0,
        # cppstd=17, libc++).  R18: prefer a dependency that has a prebuilt
        # binary over one that would have to be built from source.
        self.tool_requires("flex/2.6.4.2")
        # root CMakeLists.txt:395 find_package(PkgConfig REQUIRED) on the
        # VPR_USE_EZGL=auto path; and Yosys's Makefile uses PKG_CONFIG for
        # libffi/tcl probing.
        self.tool_requires("pkg-config/0.29.2")

    # ------------------------------------------------------------------ #
    # source
    # ------------------------------------------------------------------ #
    def source(self):
        # `sources` is an ordered list (see conandata.yml): [0] VTR itself,
        # [1] prettytable, [2] wcwidth.  Keeping all three in `sources` means
        # the build pipeline's prefetch step stages and checksum-verifies every
        # one of them, so the worker never has to fetch Python packages itself.
        srcs = self.conan_data["sources"]
        # strip_root=True throughout: each archive has a single top directory.
        get(self, **srcs[0], strip_root=True)
        get(self, **srcs[1], destination=self._py_src("prettytable"), strip_root=True)
        get(self, **srcs[2], destination=self._py_src("wcwidth"), strip_root=True)
        # java.capnp is a plain file, not an archive, so it must NOT go through
        # get(): that helper derives the name from the URL tail (`java.capnp`),
        # cannot classify it, and falls back to unzipping it, which fails with
        #     BadZipFile: File is not a zip file
        # download() performs the fetch and sha256 check without extracting.
        os.makedirs(self._schema_dir(), exist_ok=True)
        download(self, srcs[3]["url"],
                 os.path.join(self._schema_dir(), "java.capnp"),
                 sha256=srcs[3]["sha256"])

    # ------------------------------------------------------------------ #
    # environment helpers
    # ------------------------------------------------------------------ #
    def _dep_flags(self):
        """-I / -L / -l for every host dependency.

        Yosys's Makefile reads CXXFLAGS and LIBS from the *environment*
        (`CXXFLAGS := $(CXXFLAGS) ...`), and VTR invokes it as a plain
        `make ENABLE_ABC=0 PREFIX=...` with no chance to add flags, so the
        dependency search paths have to arrive through the environment.
        """
        inc, libdir, libs = [], [], []
        for _name, dep in self.dependencies.host.items():
            if dep is None or not dep.package_folder:
                continue
            for p in dep.cpp_info.aggregated_components().includedirs:
                inc.append("-I" + p)
            for p in dep.cpp_info.aggregated_components().libdirs:
                libdir.append("-L" + p)
            for lib in dep.cpp_info.aggregated_components().libs:
                libs.append("-l" + lib)
        return " ".join(inc), " ".join(libdir), " ".join(libs)

    def _dep_lib_dirs(self):
        """Dependency lib directories without the -L prefix, for the RPATH.

        abc, ace and yosys link dependency shared libraries (libtcl8.6.so in
        particular) but come out with no RPATH at all, so on the device they
        abort before main() with

            Error loading shared library libtcl8.6.so: (needed by ...)

        The path is baked in at link time by generate(), never patched in
        afterwards.
        """
        dirs = []
        for _name, dep in self.dependencies.host.items():
            if dep is None or not dep.package_folder:
                continue
            for p in dep.cpp_info.aggregated_components().libdirs:
                if p and p not in dirs:
                    dirs.append(p)
        return dirs

    def _bison_datadir(self):
        """<bison package>/share/bison -- the skeleton dir bison must be told about.

        Same defect the repository's standalone yosys recipe documents: the
        conan bison binary otherwise looks for its m4 skeleton under
        /share/bison, which does not exist.
        """
        for deps in (self.dependencies.build, self.dependencies.host):
            dep = deps.get("bison")
            if dep is not None and dep.package_folder:
                cand = os.path.join(dep.package_folder, "share", "bison")
                if os.path.isdir(cand):
                    return cand
        return ""

    def _tcl_version(self):
        """Conan tcl version as Yosys spells it: tcl<major>.<minor> (e.g. tcl8.6)."""
        dep = self.dependencies.get("tcl")
        if dep is None:
            return ""
        parts = str(dep.ref.version).split(".")
        return "tcl" + ".".join(parts[:2]) if len(parts) >= 2 else ""

    def _tclsh_shim(self):
        """Put a `tclsh` on PATH pointing at the conan tcl package's tclsh8.6.

        Belt and braces next to TCL_VERSION: yosys/Makefile:409 shells out to a
        bare `tclsh`, and the tcl package only ships `bin/tclsh8.6`.
        """
        tcl = self.dependencies.get("tcl")
        if tcl is None or not tcl.package_folder:
            return ""
        found = sorted(glob.glob(os.path.join(tcl.package_folder, "bin", "tclsh*")))
        if not found:
            return ""
        shim = os.path.join(self.generators_folder, "shim")
        os.makedirs(shim, exist_ok=True)
        path = os.path.join(shim, "tclsh")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nexec "%s" "$@"\n' % found[0])
        os.chmod(path, 0o755)
        self.output.info("  [ok] tclsh shim -> %s" % found[0])
        return shim

    def _dep_bin_dirs(self):
        """bin directories of host+build requirements that must be on PATH.

        Yosys's Makefile probes for a `tclsh` executable to work out
        TCL_VERSION, and the conan tcl package ships bin/tclsh8.6.
        """
        dirs = []
        for dep in list(self.dependencies.host.values()) + list(self.dependencies.build.values()):
            if dep is None or not dep.package_folder:
                continue
            for b in dep.cpp_info.aggregated_components().bindirs:
                if os.path.isdir(b):
                    dirs.append(b)
        return dirs

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["VPR_USE_EZGL"] = "on" if self.options.with_graphics else "off"
        tc.variables["WITH_ODIN"] = bool(self.options.with_odin)
        tc.variables["WITH_ABC"] = True
        tc.variables["WITH_PARMYS"] = True
        tc.variables["WITH_BLIFEXPLORER"] = False
        tc.variables["VTR_ENABLE_CAPNPROTO"] = bool(self.options.with_capnproto)
        # Upstream default; stated explicitly so the build cannot drift into -Werror.
        tc.variables["VTR_ENABLE_STRICT_COMPILE"] = False
        # No PGO: VTR's release_pgo path runs the titan benchmark suite mid-build,
        # which needs network downloads and many hours.
        tc.variables["VTR_IPO_BUILD"] = "off"
        # Use the pinned java.capnp instead of letting CMake wget it from
        # capnproto-java's master branch mid-build (patch 0002).  When the
        # variable is absent patch 0002 keeps upstream's download path.
        java_capnp = self._java_capnp_schema()
        if java_capnp:
            tc.variables["VTR_JAVA_CAPNP_SCHEMA"] = java_capnp
        # abc, ace and yosys link dependency shared libraries but carry no
        # RPATH, so on device they die before main() with
        #     Error loading shared library libtcl8.6.so: (needed by ...)
        # Bake the search path in at *link* time.  It has to be link time and
        # not install time: the OHOS linker self-signs the ELF it produces, and
        # anything that rewrites the file later (patchelf, or CMAKE_INSTALL_RPATH
        # applied on the way out) invalidates that signature -- an ELF with an
        # inconsistent .codesign is refused by the loader outright.  Hence
        # CMAKE_BUILD_WITH_INSTALL_RPATH=ON.  See _dep_lib_dirs().
        dep_lib_dirs = self._dep_lib_dirs()
        if dep_lib_dirs:
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
            tc.variables["CMAKE_INSTALL_RPATH"] = ":".join(dep_lib_dirs)
        tc.generate()

        inc, libdir, libs = self._dep_flags()
        env = Environment()
        # R33: values come from conan's own dependency graph, never from bare
        # shell variables.  VTR runs Yosys's Makefile from CMake as a plain
        # `make ENABLE_ABC=0 PREFIX=...`; that Makefile has CONFIG=none, whose
        # branch does NOT set CXX, so $(CXX) is taken straight from the
        # environment.  Anything stale in the caller's environment would then
        # be used verbatim, so pin both compilers to the profile's executables.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        if compilers.get("c"):
            env.define("CC", compilers["c"])
        if compilers.get("cpp"):
            env.define("CXX", compilers["cpp"])
        # Yosys's Makefile appends to CXXFLAGS, so an environment prefix is
        # preserved (a make command-line assignment would clobber its own -I.).
        # Include dirs go in the *compile* flags only; the -L/-l pair goes in
        # LIBS, which is what Yosys's link rule consumes.  Passing -L during
        # compilation is merely noise (clang warns "-Wunused-command-line-argument"
        # for every one of them, on every translation unit).
        env.define("CXXFLAGS", inc.strip())
        env.define("CFLAGS", inc.strip())
        env.define("LIBS", (libdir + " " + libs).strip())
        # Yosys is linked by its own Makefile, so it never sees the CMake RPATH
        # variables set above -- it needs the same search path as a bare linker
        # flag.  (Its binary is re-signed in package() anyway; the OHOS linker
        # signs before that, so the RPATH still has to be present at link time.)
        env.define("LDFLAGS",
                   (libdir + " " + " ".join("-Wl,-rpath," + d for d in dep_lib_dirs)).strip())
        # The conan bison package keeps its skeleton under <pkg>/share/bison.
        # Without BISON_PKGDATADIR bison looks in /share/bison and dies with
        #     bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file
        # which is what kills Yosys's parser generation steps.
        bison_datadir = self._bison_datadir()
        if bison_datadir:
            env.define("BISON_PKGDATADIR", bison_datadir)
        # yosys/Makefile:409 derives TCL_VERSION by running `tclsh`, but the
        # tcl conan package ships only bin/tclsh8.6 -- without this the probe
        # fails with "tclsh: command not found".  TCL_VERSION is `?=` there, so
        # supplying it in the environment removes the need for tclsh at all.
        tcl_version = self._tcl_version()
        if tcl_version:
            env.define("TCL_VERSION", tcl_version)
        shim = self._tclsh_shim()
        if shim:
            env.prepend_path("PATH", shim)
        # Yosys finds libffi/tcl through pkg-config; PkgConfigDeps writes the
        # .pc files but does not extend PKG_CONFIG_PATH by itself.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # R10: OHOS has no writable /tmp and no /bin/sh for ELF exec.
        env.define("CONFIG_SHELL", os.environ.get("CONFIG_SHELL", "/bin/sh"))
        for d in self._dep_bin_dirs():
            env.prepend_path("PATH", d)
        env.vars(self, scope="build").save_script("conanbuildenv-vtr")

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.settings.os in ("Linux", "OHOS"):
            self._run_unit_tests()

    # ------------------------------------------------------------------ #
    # unit tests (upstream's CTest suite)
    # ------------------------------------------------------------------ #
    def _run_unit_tests(self):
        """Run upstream's four Catch2 unit-test binaries.

        Upstream registers them with add_test() (vpr/CMakeLists.txt:328) and
        runs them via CTest, which is what `make test` forwards to.  The three
        small binaries -- test_archfpga, test_vtrutil, test_fasm -- are run by
        CTest unchanged.

        test_vpr is not, because upstream registers its 60 TEST_CASEs as ONE
        ctest test that executes them all in a single process, and two of those
        cases cannot share a process:

            test_compressed_grid   publishes test-local objects into the
                                   process-global g_vpr_ctx device context
                                   (grid_, logical_block_types,
                                   EMPTY_PHYSICAL_TILE_TYPE) and never resets
                                   it, so any case that later runs a full
                                   vpr_init()/vpr_free_all() cycle faults.
            connection_router      is such a case.

        Both orders fault, so no ordering avoids it.  Measured on device:

            test_vpr "test_compressed_grid,connection_router"  -> SIGSEGV
            test_vpr "connection_router,test_compressed_grid"  -> SIGSEGV
            test_vpr "test_compressed_grid"                    -> ok
            test_vpr "connection_router"                       -> ok
            test_vpr "~[vpr_compressed_grid]"                  -> ok

        Upstream CI never invokes CTest (no workflow under .github/workflows/
        runs it or `make test`), which is why the defect is latent there.  It is
        a property of the two test cases, not of this platform: no file touched
        by patches 0001-0005 is on either path.

        Nothing is skipped and no assertion is relaxed -- the 60 cases are run
        as two groups so that each case executes in a process that does not
        also contain the other half of the conflicting pair.
        """
        if self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            return

        self.run(f'ctest --output-on-failure --test-dir "{self.build_folder}" '
                 f'-E "^test_vpr$"',
                 env="conanbuild")

        # test_vpr resolves its inputs (wire.eblif, testarch.device) and
        # ../../vtr_flow relative to the working directory, which is why
        # upstream sets WORKING_DIRECTORY to the source-side vpr/test.
        test_dir = os.path.join(self.source_folder, "vpr", "test")
        test_bin = os.path.join(self.build_folder, "vpr", "test_vpr")
        for group in ("~[vpr_compressed_grid]", "[vpr_compressed_grid]"):
            self.run(f'cd "{test_dir}" && "{test_bin}" --colour-mode none "{group}"',
                     env="conanbuild")

    # ------------------------------------------------------------------ #
    # python runtime modules (see conandata.yml)
    # ------------------------------------------------------------------ #
    def _py_src(self, name):
        return os.path.join(self.source_folder, "_py", name)

    def _schema_dir(self):
        return os.path.join(self.source_folder, "_schema")

    def _java_capnp_schema(self):
        """Path to the pinned java.capnp, or "" if it is not present."""
        cand = os.path.join(self._schema_dir(), "java.capnp")
        return cand if os.path.isfile(cand) else ""

    def _package_python_runtime(self):
        """Ship the Python modules the packaged flow imports at run time.

        `import vtr` (done by run_vtr_flow.py / run_vtr_task.py /
        run_reg_test.py) pulls in `from prettytable import PrettyTable` at
        module scope, and prettytable renders through wcwidth.  Without both the
        flow and the upstream regression runner cannot start at all, so they are
        installed next to the tools and advertised on PYTHONPATH.

        Copied directly rather than pip-installed: both are pure Python with no
        further dependencies, and a plain copy keeps the build free of any pip /
        network / build-isolation assumptions on the worker.
        """
        site = os.path.join(self.package_folder, "lib", "python", "site-packages")
        os.makedirs(site, exist_ok=True)

        # prettytable's sdist keeps the package under src/; wcwidth's is at the
        # root of the tree.
        wanted = (("prettytable", ("src/prettytable", "prettytable")),
                  ("wcwidth", ("wcwidth", "src/wcwidth")))
        for name, candidates in wanted:
            for rel in candidates:
                cand = os.path.join(self._py_src(name), *rel.split("/"))
                if os.path.isdir(cand) and glob.glob(os.path.join(cand, "*.py")):
                    copy(self, "*.py", src=cand, dst=os.path.join(site, name))
                    self.output.info("  [ok] vendored python module: %s" % name)
                    break
            else:
                raise ConanInvalidConfiguration(
                    "vendored python module %r not found under %s (looked in %s)"
                    % (name, self._py_src(name), ", ".join(candidates)))

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #
    def package(self):
        cmake = CMake(self)
        cmake.install()

        # licenses
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # ---- the flow tree the scripts drive -------------------------------
        # vtr_flow/ carries scripts, parse rules, tasks, architectures and
        # benchmarks; without it run_vtr_task.py has nothing to run.
        for sub in ("vtr_flow", "utils"):
            copy(self, "*", src=os.path.join(self.source_folder, sub),
                 dst=os.path.join(self.package_folder, sub))

        # Upstream's documented regression entry points live at the repository
        # root, not inside vtr_flow/.  They resolve everything from their own
        # location (paths.py walks five levels up from
        # vtr_flow/scripts/python_libs/vtr/paths.py), so dropping them next to
        # vtr_flow/ is exactly what makes `./run_quick_test.py` and
        # `./run_reg_test.py <suite>` -- the commands in BUILDING.md and
        # README.developers.md -- runnable from the installed package.
        for entry in ("run_quick_test.py", "run_reg_test.py", "sweep_build_configs.py"):
            copy(self, entry, src=self.source_folder, dst=self.package_folder)

        # Per-component regression drivers referenced by paths.py.
        if self.options.with_odin:
            copy(self, "verify_odin.sh", src=os.path.join(self.source_folder, "odin_ii"),
                 dst=os.path.join(self.package_folder, "odin_ii"))
            copy(self, "regression_test/*", src=os.path.join(self.source_folder, "odin_ii"),
                 dst=os.path.join(self.package_folder, "odin_ii"))
        copy(self, "verify_parmys.sh", src=os.path.join(self.source_folder, "parmys"),
             dst=os.path.join(self.package_folder, "parmys"))
        copy(self, "regression_test/*", src=os.path.join(self.source_folder, "parmys"),
             dst=os.path.join(self.package_folder, "parmys"))
        copy(self, "third_party/*", src=os.path.join(self.source_folder, "parmys"),
             dst=os.path.join(self.package_folder, "parmys"))
        # ABC's runtime resource file is read by the flow (paths.abc_rc_path).
        copy(self, "abc.rc", src=os.path.join(self.source_folder, "abc"),
             dst=os.path.join(self.package_folder, "abc"))
        # ---- tools that upstream builds but never installs --------------
        # `make install` produces bin/vpr, bin/ace, bin/odin_ii, bin/rtl_number
        # and bin/genfasm -- but NOT bin/abc and NOT bin/yosys:
        #   abc    abc/CMakeLists.txt:103 declares `add_executable(abc ...)`
        #          and the file carries no install() rule at all.
        #   yosys  is built by its own Makefile into <CMAKE_BINARY_DIR>/bin/.
        # Upstream does not need them installed: it reaches abc through the
        # committed symlink abc/abc -> ../build/abc/abc and yosys through
        # <root>/build/bin/yosys, both of which assume CMAKE_BINARY_DIR is
        # exactly <source>/build.  Under conan's cmake_layout the build tree is
        # elsewhere, so the symlink is dangling (verified: both the source-side
        # and the build-side copy of it fail to resolve) and the package would
        # ship without ABC and without Yosys -- i.e. with no synthesis and no
        # technology mapping at all.  Pull both out of the build tree into bin/,
        # where the entry-point pass below expects every tool to be; it then
        # lays them down at abc/abc and build/bin/yosys like the rest.
        built_tools = {
            "abc": (os.path.join(self.build_folder, "abc", "abc"),
                    os.path.join(self.build_folder, "abc", "Release", "abc")),
            "yosys": (os.path.join(self.build_folder, "bin", "yosys"),),
        }
        bindir = os.path.join(self.package_folder, "bin")
        for tool, candidates in built_tools.items():
            if os.path.isfile(os.path.join(bindir, tool)):
                continue  # install() already provided it (prebuilt/VTR change)
            built = next((c for c in candidates
                          if os.path.isfile(c) and not os.path.islink(c)), None)
            if built is None:
                raise ConanInvalidConfiguration(
                    "%s was not built: none of %s exists.  It is part of the "
                    "CAD chain (WITH_ABC / WITH_PARMYS must stay ON)"
                    % (tool, ", ".join(candidates)))
            os.makedirs(bindir, exist_ok=True)
            dst = os.path.join(bindir, tool)
            shutil.copy2(built, dst)
            os.chmod(dst, 0o755)
            self.output.info("  [ok] staged %s from the build tree: %s"
                             % (tool, built))

        # yosys is the ONE tool linked by its own Makefile, so it inherits
        # neither the CMake RPATH nor the OHOS self-signature that the CMake
        # link rules produce.  Both omissions were measured on the device:
        #   * no RPATH   -> "Error loading shared library libtcl8.6.so"
        #   * .codesign records 194168448 for a 17860432-byte file -> EPERM
        #     ("Operation not permitted"); removing the section instead gives
        #     EACCES ("Permission denied"), so only a re-signing works.
        # vpr, odin_ii, rtl_number, abc and ace come out of the CMake link with
        # a self-consistent signature AND a working RPATH; they are left alone.
        if self.settings.os == "OHOS":
            self._fix_yosys_for_ohos(os.path.join(bindir, "yosys"))

        # ACE needs its helper scripts (paths.get_ace_extract_clk_script_path).
        copy(self, "scripts/*", src=os.path.join(self.source_folder, "ace2"),
             dst=os.path.join(self.package_folder, "ace2"))
        for supp in ("valgrind.supp", "lsan.supp", "asan.supp"):
            copy(self, supp, src=os.path.join(self.source_folder, "vpr"),
                 dst=os.path.join(self.package_folder, "vpr"))

        self._materialise_tool_entry_points()
        self._package_python_runtime()

    def _fix_yosys_for_ohos(self, path):
        """Make the packaged yosys runnable with no conanrun environment.

        Three steps, and the order is forced by the OHOS loader:

          1. bundle the non-system shared libraries it needs into <pkg>/lib and
             <pkg>/build/lib,
          2. set its RUNPATH to $ORIGIN/../lib -- which resolves to <pkg>/lib
             from <pkg>/bin/yosys and to <pkg>/build/lib from the copy that
             lands at <pkg>/build/bin/yosys,
          3. drop the stale .codesign and self-sign.

        Step 3 must come last: `binary-sign-tool` refuses a file that still has
        a .codesign section, and ANY write to the ELF after signing invalidates
        the signature -- which is precisely how yosys ended up unloadable.
        """
        if not os.path.isfile(path):
            return
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
        missing_tools = [n for n, p in (("llvm-objcopy", objcopy),
                                        ("binary-sign-tool", signer),
                                        ("patchelf", patchelf),
                                        ("readelf", readelf))
                         if not p or not os.path.exists(p)]
        if missing_tools:
            raise ConanInvalidConfiguration(
                "cannot make yosys standalone on OHOS: %s not found.  Without "
                "this the packaged yosys is rejected by the loader or cannot "
                "find libtcl8.6.so." % ", ".join(missing_tools))

        # 1. bundle what the dependency packages actually ship.  This is
        #    best-effort on purpose: readelf says yosys needs libtcl8.6.so and
        #    libtcl8.6.so needs libz.so, but the conan zlib package here is
        #    static-only (libz.a) and the OHOS system carries libz.so.1 rather
        #    than libz.so -- and yosys nevertheless loads and runs with only
        #    libtcl8.6.so bundled.  Hard-failing on an assumed library list
        #    would break the build over something that demonstrably works, so
        #    the list is best-effort and step 4 is the real gate.
        dest_dirs = [os.path.join(self.package_folder, "lib"),
                     os.path.join(self.package_folder, "build", "lib")]
        bundled, absent = [], []
        for name in ("libtcl8.6.so", "libz.so"):
            family = []
            for d in self._dep_lib_dirs():
                family = sorted(f for f in glob.glob(os.path.join(d, name + "*"))
                                if os.path.isfile(f))
                if family:
                    break
            if not family:
                absent.append(name)
                continue
            for src in family:
                for d in dest_dirs:
                    os.makedirs(d, exist_ok=True)
                    shutil.copy2(src, os.path.join(d, os.path.basename(src)))
            bundled.append(name)
        self.output.info("  [ok] bundled for standalone yosys: %s -> %s"
                         % (", ".join(bundled) or "<none>", ", ".join(dest_dirs)))
        if absent:
            self.output.info(
                "  [i]  not shipped by any dependency (relied on from the "
                "system): %s" % ", ".join(absent))

        # 2. RUNPATH (before signing -- see the docstring).
        #    $ORIGIN must reach patchelf literally.  self.run() goes through a
        #    shell, and double quotes do NOT protect it: "$ORIGIN" is expanded
        #    to the empty string and the ELF ends up with /../lib, which the
        #    loader cannot use.  Single quotes are required here.
        self.run(f"\"{patchelf}\" --set-rpath '$ORIGIN/../lib' \"{path}\"")

        # Read it back.  A silently wrong RUNPATH costs a full rebuild to
        # discover and has already happened once: with double quotes the shell
        # expanded "$ORIGIN" to nothing and the ELF got /../lib.
        buf = io.StringIO()
        self.run(f'"{readelf}" -d "{path}"', stdout=buf)
        rpath_lines = [l.strip() for l in buf.getvalue().splitlines()
                       if "RPATH" in l or "RUNPATH" in l]
        if not any("$ORIGIN/../lib" in l for l in rpath_lines):
            raise ConanInvalidConfiguration(
                "RUNPATH not set correctly on %s -- readelf says: %s"
                % (path, rpath_lines or "<no RPATH/RUNPATH entry at all>"))

        # 3. strip the stale signature, then self-sign
        unsigned = path + ".unsigned"
        signed = path + ".signed"
        self.run(f'"{objcopy}" --remove-section=.codesign "{path}" "{unsigned}"')
        self.run(f'"{signer}" sign -inFile "{unsigned}" -outFile "{signed}" '
                 f'-selfSign 1 -signAlg SHA256withECDSA')
        os.replace(signed, path)
        os.remove(unsigned)
        os.chmod(path, 0o755)
        self.output.info("  [ok] yosys RUNPATH=$ORIGIN/../lib, re-signed: %s" % path)

        # 4. the real gate.  Run it under exactly the condition the user-facing
        #    tools see: LD_LIBRARY_PATH removed and no conanrun env sourced.
        #    This is what decides whether the packaging above was sufficient --
        #    not the library list guessed in step 1.
        buf = io.StringIO()
        self.run(f'env -u LD_LIBRARY_PATH "{path}" --version', stdout=buf)
        text = buf.getvalue().strip()
        first = (text.splitlines() or ["<no output>"])[0]
        if "Yosys" not in text:
            raise ConanInvalidConfiguration(
                "the packaged yosys does not run without conanrun: "
                "`env -u LD_LIBRARY_PATH %s --version` said: %s" % (path, first))
        self.output.info("  [ok] standalone yosys check: %s" % first)

    def _materialise_tool_entry_points(self):
        """Recreate the tool paths paths.py expects, from what install() produced.

        Upstream uses committed symlinks into the build tree; a package cannot
        carry a link into a build tree that no longer exists, so the binaries
        are copied to the same relative locations instead.  Copies (not
        symlinks) keep the package relocatable and survive tar packaging.
        """
        bindir = os.path.join(self.package_folder, "bin")

        def installed(*names):
            for n in names:
                p = os.path.join(bindir, n)
                if os.path.isfile(p) and not os.path.islink(p):
                    return p
                # shared-library builds may land with a version suffix
                for cand in sorted(glob.glob(p + ".*")):
                    if os.path.isfile(cand):
                        return cand
            return None

        mapping = {
            "abc/abc": ("abc",),
            "vpr/vpr": ("vpr",),
            "ace2/ace": ("ace",),
            "odin_ii/odin_ii": ("odin_ii",),
            "libs/librtlnumber/rtl_number": ("rtl_number",),
        }
        for rel, names in mapping.items():
            if rel.startswith("odin_ii/") and not self.options.with_odin:
                continue
            src = installed(*names)
            if src is None:
                if rel.startswith("odin_ii/"):
                    continue
                raise ConanInvalidConfiguration(
                    "expected installed binary %r in bin/ but it is missing" % (names,))
            dst = os.path.join(self.package_folder, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)

        # paths.py looks for Yosys at <root>/build/bin/yosys.
        yosys_bin = installed("yosys")
        if yosys_bin:
            dst_dir = os.path.join(self.package_folder, "build", "bin")
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(yosys_bin, os.path.join(dst_dir, "yosys"))
            os.chmod(os.path.join(dst_dir, "yosys"), 0o755)

    # ------------------------------------------------------------------ #
    # metadata
    # ------------------------------------------------------------------ #
    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        # libvpr/libvtrutil/libarchfpga are installed to bin/ upstream
        # (install(TARGETS ... DESTINATION bin)), so advertise that too.
        self.cpp_info.libdirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define("VTR_ROOT", self.package_folder)
        # the packaged flow imports prettytable (and prettytable imports
        # wcwidth) at module scope -- see _package_python_runtime()
        self.runenv_info.prepend_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", "python", "site-packages"))
