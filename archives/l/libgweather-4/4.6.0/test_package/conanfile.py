import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libgweather4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Align with the main recipe's dependency line (shared published
        # graph). Only linkage-visible deps are declared here: the
        # data-only gweather-locations and the pruned transitive deps are
        # NOT required directly (direct-requiring the data package makes
        # CMakeDeps emit a target with its nonexistent include/ dir) —
        # their runtime paths (LIBGWEATHER_LOCATIONS_PATH / TZDIR /
        # GSETTINGS_SCHEMA_DIR) are exported by the libgweather-4 recipe
        # itself via runenv_info and reach this test through conanrun.
        # geocode-glib 3.26.4 test_package precedent.
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("json-glib/1.10.6")
        self.requires("libsoup3/3.6.5-r3")

    def layout(self):
        cmake_layout(self)

    # Subtrees pruned from dependency package lib scans (no shared libs are
    # shipped there; bounds os.walk cost). Same policy as the main recipe.
    _WALK_PRUNE = ("include", "share", "bin", "pkgconfig", "cmake", "man",
                   "doc", "licenses", "__pycache__")

    def _prepare_test_libs(self, shadow):
        """Consumer-side twin of the main recipe's _prepare_test_libs().

        Rationale (official worker PR #15863, round 2): the ohpcd
        json-glib/1.10.6 artifact's .codesign signature is rejected by the
        OHOS loader, and the consumer load chain test exe ->
        libgweather-4.so.0 -> libgeocode-glib-2.so.0 -> libjson-glib-1.0.so.0
        hits it here exactly like the upstream TAP phase does. A local PASS
        does not transfer (local cache copies were re-signed in place; the
        worker unpacks the raw artifact — test_package has never run there).
        So: os.walk each dependency package folder, copy the real ELF .so
        files into a flat shadow dir, strip .codesign and re-sign with
        binary-sign-tool (same pattern as the main recipe / package()),
        mirror symlink names onto the signed copies, and prepend the shadow
        dir to the test's LD_LIBRARY_PATH — consumer resolution then depends
        on neither artifact signature nor layout state.
        The shadow is purged and rebuilt on every test() run: a stale
        shadow carrying copies of an already-sabotaged dependency would
        mask the CI's L1e destructive negative test (R34).
        """
        if os.path.isdir(shadow):
            shutil.rmtree(shadow)
        os.makedirs(shadow)
        _objcopy = os.path.join(os.path.dirname(
            os.path.realpath("/data/service/hnp/bin/clang")), "llvm-objcopy")
        _signtool = os.path.realpath("/data/service/hnp/bin/binary-sign-tool")
        links = []
        for _name, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base or not os.path.isdir(str(_base)):
                continue
            for _root, _dnames, _fnames in os.walk(str(_base), topdown=True):
                _dnames[:] = [x for x in _dnames if x not in self._WALK_PRUNE]
                for _f in _fnames:
                    if not _f.endswith(".so") and ".so." not in _f:
                        continue
                    _src = os.path.join(_root, _f)
                    if os.path.islink(_src):
                        links.append((_f, os.path.basename(os.readlink(_src))))
                        continue
                    if not os.path.isfile(_src):
                        continue
                    with open(_src, "rb") as _fh:
                        if _fh.read(4) != b"\x7fELF":
                            continue  # not a runtime lib (e.g. lib*.so.*.symbols text)
                    _dst = os.path.join(shadow, _f)
                    if os.path.exists(_dst):
                        continue
                    shutil.copy2(_src, _dst)
                    self.run('"%s" --remove-section=.codesign "%s"'
                             % (_objcopy, _dst), ignore_errors=True)
                    self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                             % (_signtool, _dst, _dst))
                    os.chmod(_dst, 0o755)
                    self.output.info("test-libs: signed copy of %s" % _f)
        _progress = True
        while _progress:
            _progress = False
            for _lname, _tname in links:
                _l = os.path.join(shadow, _lname)
                if os.path.lexists(_l):
                    continue
                if os.path.exists(os.path.join(shadow, _tname)):
                    os.symlink(_tname, _l)
                    _progress = True
        return shadow

    def build(self):
        # hnp cmake is an OHOS ELF: needs /system/lib64's libc++_shared.so
        # (gtksourceview5 / geocode-glib precedent).
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        libdirs = []
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None) or ""
            for _p in (_d.cpp_info.libdirs or []):
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs and os.path.isdir(_p):
                    libdirs.append(_p)
        _exe_dir = self.cpp.build.bindirs[0]
        shadow = self._prepare_test_libs(os.path.join(_exe_dir, "test-libs"))
        ldpath = os.pathsep.join([shadow] + libdirs)
        # Runtime data env is shipped inside the package itself
        # (share/gweather-4/runtime-env.sh: LIBGWEATHER_LOCATIONS_PATH,
        # GSETTINGS_SCHEMA_DIR, TZDIR) — env piping through the conan
        # graph is unreliable on this host (empty conanrun.sh).
        gw_pkg = self.dependencies["libgweather-4"].package_folder
        env_sh = os.path.join(str(gw_pkg), "share", "gweather-4", "runtime-env.sh")
        assert os.path.isfile(env_sh), "runtime-env.sh missing: %s" % env_sh
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libgweather4")
        cmd = (
            ". {env}; export LIBGWEATHER_LOCATIONS_PATH GSETTINGS_SCHEMA_DIR TZDIR; "
            "export LD_LIBRARY_PATH=\"{ld}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            "[ -f \"$LIBGWEATHER_LOCATIONS_PATH\" ] "
            "|| {{ echo \"Locations.bin missing: $LIBGWEATHER_LOCATIONS_PATH\"; exit 1; }}; "
            "[ -f \"$TZDIR/Europe/Paris\" ] "
            "|| {{ echo \"TZDIR tree missing: $TZDIR\"; exit 1; }}; "
            "env GIO_USE_VFS=local {exe}"
        ).format(env=shlex.quote(env_sh), ld=ldpath, exe=shlex.quote(exe))
        self.run("%s -c '%s'" % (bash, cmd), env="conanrun")
