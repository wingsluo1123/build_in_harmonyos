#!/usr/bin/env python3
"""Conan recipe for palabos 2.3.01 (CMake, static library).

Palabos is an open-source CFD solver based on the lattice Boltzmann method.
Upstream provides no automated test suite (no tests/ directory, no ctest
entries; upstream CI only compiles the examples). This recipe builds only
the static palabos library (CI=OFF, ENABLE_MPI=OFF) and packages headers
plus the static archive for OHOS aarch64.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class PalabosConan(ConanFile):
    name = "palabos"
    version = "2.3.01"
    description = "Open-source CFD solver based on the lattice Boltzmann method."
    license = "AGPL-3.0-or-later"
    homepage = "https://palabos.unige.ch"
    url = "https://gitlab.com/unigespc/palabos"
    topics = ("cfd", "lattice-boltzmann", "simulation")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_compiler(self, configured, names):
        # Tool-specific candidates only: never fall back from C to C++
        # names or vice versa. Prefer the profile's configured absolute
        # path when it exists (CI workers), otherwise resolve via PATH
        # or the ~/usr/local/bin fallback (zydis/4.1.1 _resolve_compiler
        # precedent: the shared ohos-aarch64 profile still points at
        # /data/service/hnp/bin/clang which is ENOENT on current
        # preflight workers, so project() fails its compiler check).
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def _ninja_path(self):
        # Conditional Ninja probe: prefer the HMBS-injected absolute path,
        # then the user.hmbs:ninja_path conf, then PATH. Returns None when
        # ninja is unavailable so callers fall back to the default
        # (Unix Makefiles) generator. Verified with os.path.exists so a
        # stale pointer never forces a generator the worker cannot run.
        cand = os.getenv("HMBS_NINJA")
        if cand and os.path.exists(cand):
            return cand
        try:
            conf_ninja = self.conf.get("user.hmbs:ninja_path",
                                       default=None)
        except Exception:
            conf_ninja = None
        if conf_ninja and os.path.exists(conf_ninja):
            return conf_ninja
        found = shutil.which("ninja")
        if found and os.path.exists(found):
            return found
        return None

    def _ensure_writable_tmp(self):
        # Reuse the HMBS-injected writable TMPDIR/TMP/TEMP (plus HOME/tmp
        # and a build-local fallback) so CMake compiler checks and clang
        # temp files can write. Only redirects the temp root.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                import json as _json
                tmpdir = _json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # The toolchain.cache_variables pin alone did not override the
        # stale profile compiler on the true device (zydis/4.1.1
        # preflight evidence), so correct the generated artifact itself
        # and export CC/CXX in build scope -- only when the configured
        # path is missing and the resolved one exists (CI workers
        # untouched).
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
                for line in text.splitlines():
                    s = line.strip()
                    if "CMAKE_C_COMPILER" in s or "CMAKE_CXX_COMPILER" in s:
                        self.output.info("HMBS diag toolchain %s" % s)
            else:
                self.output.warning(
                    "HMBS diag toolchain file not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % e)

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        # Persist writable tmp through Conan's build scope so that the
        # CMake try_compile spawned by project() inherits it even if the
        # outer shell sanitizes os.environ.
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("GOTMPDIR", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        # CI #93575: CMake's Unix Makefiles TryCompile shells out through
        # /bin/sh (Makefile SHELL=/bin/sh) and the CI worker failed the
        # compiler self-check with "/bin/sh: can't fork - try again"
        # AFTER compiler identification had already passed (Clang 15.0.4).
        # Prefer the Ninja generator when a real ninja binary exists
        # (aws-lc-tools/5.2.0 OHOS precedent: less CMake/Make per-target
        # overhead under the single-job budget). Ninja drives the compiler
        # directly without the /bin/sh+make fork path, so a transient
        # EAGAIN on /bin/sh no longer fails configure. Fully conditional:
        # without ninja we keep the previous Makefiles behaviour, and the
        # log carries the chosen generator for ground truth.
        _ninja = self._ninja_path()
        if str(self.settings.os) == "OHOS" and _ninja:
            tc = CMakeToolchain(self, generator="Ninja")
            self.output.info("HMBS diag generator=Ninja ninja=%s" % _ninja)
        else:
            tc = CMakeToolchain(self)
            self.output.info("HMBS diag generator=Makefiles ninja=%s"
                             % (_ninja,))
        # Upstream root CMakeLists.txt declares cmake_minimum_required(<3.5);
        # CMake 4.x on the device rejects it without this compat floor.
        # Must go through cache_variables (variables is too late for the
        # early policy check).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CI #94119: Ninja TryCompile passed compile [1/2] but the link
        # [2/2] (`: && clang ... && :` via /bin/sh) died with
        # "/bin/sh: can't fork - try again" -- worker-side EAGAIN, while
        # the same commit passed TryCompile on another worker (CI-001
        # #94047 reached CMake.build()). The toolchain compiler is proven
        # (identification prints Clang 15.0.4; preflight built the full
        # static lib), so skip the redundant compiler self-check and
        # downgrade any remaining try_compiles to compile-only static
        # libraries (extra-cmake-modules/6.28.0 + cryptokit/1.21.1
        # precedent: CMAKE_C/CXX_COMPILER_WORKS avoids TryCompile link
        # failures; STATIC_LIBRARY used widely, e.g. any-lite/dir ent).
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # Compiler migration (zydis/4.1.1 precedent): pin the resolved
        # compilers so conan_toolchain.cmake does not reference a missing
        # profile tool.
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # (Examples/utility gating happens in build() via _gate_examples.)
        # Upstream root CMake defaults ENABLE_MPI=ON (requires MPI). On OHOS
        # build library only, no MPI.
        tc.variables["ENABLE_MPI"] = "OFF"
        tc.variables["ENABLE_POSIX"] = "ON"
        tc.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _gate_examples(self):
        # Library-only build: comment out every
        # add_subdirectory(examples/...) / add_subdirectory(utility/...)
        # line in the upstream root CMakeLists.txt. Line-oriented and
        # independent of hunk line numbers, so it cannot fail with
        # "source file is different" the way the previous static patch
        # did (preflight: expected context mismatched at
        # examples/showCases/particlesInCone).
        path = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        gated = 0
        out = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("add_subdirectory(examples/") \
                    or stripped.startswith("add_subdirectory(utility/"):
                out.append("# HMBS library-only: " + line)
                gated += 1
            else:
                out.append(line)
        if gated == 0:
            raise RuntimeError(
                "HMBS _gate_examples found no examples/utility entries in %s"
                % path)
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
        self.output.info(
            "HMBS diag gated %d examples/utility subdirectories" % gated)

    def _fix_cxx17_random_shuffle(self):
        # std::random_shuffle was removed in C++17; the device clang
        # (C++17 default) rejects src/dataProcessors/metaStuffWrapper3D.cpp:85
        # `std::random_shuffle(ids.begin(), ids.end())`. Replace the 2-arg
        # form with std::shuffle + mt19937 (available since C++11, so the
        # result still compiles under C++11). Line/regex oriented, no hunk
        # numbers. Ensures <random> is included wherever touched.
        touched = 0
        for root, _dirs, files in os.walk(self.source_folder):
            for fn in files:
                if not fn.endswith((".cpp", ".h", ".hh", ".hpp")):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        text = f.read()
                except Exception:
                    continue
                if "random_shuffle" not in text:
                    continue
                orig = text
                if "#include <random>" not in text:
                    # Insert after the last #include line.
                    lines = text.splitlines(True)
                    last_inc = -1
                    for i, line in enumerate(lines):
                        if line.lstrip().startswith("#include"):
                            last_inc = i
                    ins = "#include <random>  // HMBS C++17 compat\n"
                    if last_inc >= 0:
                        lines.insert(last_inc + 1, ins)
                    else:
                        lines.insert(0, ins)
                    text = "".join(lines)
                # 2-arg form only (upstream uses ids.begin(), ids.end()).
                # Balanced-paren scan: (.*?) regex fails because args
                # themselves contain parens (ids.begin()/ids.end()).
                n = 0
                search_from = 0
                token = "std::random_shuffle("
                while True:
                    idx = text.find(token, search_from)
                    if idx < 0:
                        break
                    open_paren = idx + len(token) - 1
                    depth = 0
                    j = open_paren
                    arg_text = None
                    while j < len(text):
                        ch = text[j]
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                            if depth == 0:
                                arg_text = text[open_paren + 1:j]
                                break
                        j += 1
                    if arg_text is None:
                        break
                    # split top-level comma
                    d2 = 0
                    split_at = -1
                    for k, ch in enumerate(arg_text):
                        if ch == '(':
                            d2 += 1
                        elif ch == ')':
                            d2 -= 1
                        elif ch == ',' and d2 == 0:
                            split_at = k
                            break
                    if split_at < 0:
                        search_from = j + 1
                        continue
                    # reject 3-arg form: more than one top-level comma
                    rest = arg_text[split_at + 1:]
                    # count top-level commas in rest
                    d3 = 0
                    extra_comma = False
                    for ch in rest:
                        if ch == '(':
                            d3 += 1
                        elif ch == ')':
                            d3 -= 1
                        elif ch == ',' and d3 == 0:
                            extra_comma = True
                            break
                    if extra_comma:
                        search_from = j + 1
                        continue
                    a1 = arg_text[:split_at].strip()
                    a2 = rest.strip()
                    repl = "std::shuffle(" + a1 + ", " + a2 + ", std::mt19937{std::random_device{}()})"
                    text = text[:idx] + repl + text[j + 1:]
                    n += 1
                    search_from = idx + len(repl)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    touched += 1
                    rel = os.path.relpath(path, self.source_folder)
                    self.output.info(
                        "HMBS diag cxx17 shuffle fixed %s (%d calls)" % (rel, n))
        if touched:
            self.output.info(
                "HMBS diag cxx17 shuffle touched %d files" % touched)

    def build(self):
        self._fix_cxx17_random_shuffle()
        self._gate_examples()
        # Diagnose with the resolved compiler, not the stale profile path.
        try:
            comp_exes = self.conf.get("tools.build:compiler_executables",
                                      default=None)
        except Exception:
            comp_exes = None
        self.output.info("HMBS diag TMPDIR=%s TMP=%s TEMP=%s"
                         % (os.getenv("TMPDIR"), os.getenv("TMP"),
                            os.getenv("TEMP")))
        self.output.info("HMBS diag compiler_executables=%s" % (comp_exes,))
        _diag_c = None
        if isinstance(comp_exes, dict):
            _diag_c = self._resolve_compiler(comp_exes.get("c"),
                                             ("clang", "cc"))
        if _diag_c:
            self.run("%s --version" % _diag_c, ignore_errors=True)
        else:
            self.run("clang --version", ignore_errors=True)
        cmake = CMake(self)
        cmake.configure()
        # CI #94047: Conan defaulted to `-j20` (cmake --build ... -- -j20)
        # and ninja died with "posix_spawn: Resource temporarily
        # unavailable" compiling this large static library on the shared
        # worker. Serialize the native build (zarchive/0.1.2 precedent:
        # cmake.build(build_tool_args=["-j1"]); repo R9 always -j1).
        cmake.build(build_tool_args=["-j1"])
        self._emit_upstream_marker()

    def _emit_upstream_marker(self):
        """Upstream ships no test suite; emit a no_tests marker with audit."""
        searched = [
            "tests", "test", "Testing",
            "CMakeLists.txt:enable_testing",
            "CMakeLists.txt:add_test",
            ".gitlab-ci.yml:script",
        ]
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "audit-only: no enable_testing/add_test in CMakeLists.txt; CI only compiles examples",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Upstream v2.3.0 tree has no tests/ directory and no ctest entries; .gitlab-ci.yml only runs cmake+make on examples. Searched: " + ", ".join(searched),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def package(self):
        # Upstream CMake defines no install() rules, so copy artifacts manually.
        libname = "palabos.lib" if str(self.settings.os) == "Windows" else "libpalabos.a"
        found = None
        for root, _dirs, files in os.walk(self.build_folder):
            if libname in files:
                found = root
                break
        if found is None:
            raise RuntimeError("libpalabos.a not found in build tree")
        copy(self, libname, found, os.path.join(self.package_folder, "lib"))
        # Headers: src/ is the include root (e.g. <core/globalDefs.h>,
        # "palabos2D.h"). Preserve the tree under include/.
        for pattern in ("*.h", "*.hh"):
            copy(self, pattern, os.path.join(self.source_folder, "src"),
                 os.path.join(self.package_folder, "include"))
        # Vendored third-party headers referenced as <tinyxml/...>,
        # <Eigen/...> etc. via externalLibraries include dir.
        ext = os.path.join(self.source_folder, "externalLibraries")
        for sub in ("tinyxml", "Eigen", "Eigen3", "nanoflann", "sitmo"):
            src_dir = os.path.join(ext, sub)
            if os.path.isdir(src_dir):
                copy(self, "*", src_dir,
                     os.path.join(self.package_folder, "include", sub))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["palabos"]
        self.cpp_info.includedirs = ["include"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
        self.cpp_info.set_property("cmake_file_name", "palabos")
        self.cpp_info.set_property("cmake_target_name", "palabos::palabos")
