#!/usr/bin/env python3
"""Conan recipe — libgweather-4 4.6.0 (meson, GLib/libsoup3 stack)

GNOME weather and world-locations library (GWeather): world locations
database access (Locations.bin from gweather-locations), METAR parsing
and METAR/MET Norway/OWM/NWS weather backends over libsoup3. Delivers
libgweather-4.so.0, pkg-config name `gweather4` (variable
soupapiversion=3.0), headers at include/libgweather-4.0/libgweather and
the org.gnome.GWeather4 GSettings schema.

Dependency-first closure (R36): geocode-glib/3.26.4 (libsoup3 flavour)
and gweather-locations/2026.2 (Locations.bin data package) are companion
packages delivered by their own runs; they resolve from the ohpcd
registry (local conan cache as fallback).

OHOS adaptations (geocode-glib 3.26.4 recipe precedent):
  - introspection=false, gtk_doc=false, enable_vala=false
    (g-ir-scanner/vapigen cannot run against cross-built libs)
  - glib module .pc compat generation + glib tool variables patched into
    glib-2.0.pc and appended to the regenerated gio-2.0.pc (gnome.mkenums
    needs glib_mkenums; gnome.post_install resolves glib_compile_schemas
    from gio-2.0.pc at configure time)
  - gweather-locations.pc locations_db variable re-added (PkgConfigDeps
    emits only prefix/lib/include; upstream meson reads the
    `locations_db` pkg-config variable to bake GWEATHER_LOCATIONS_DB)
  - SDK llvm bin + glib tools bin prepended to PATH (meson ar detection,
    schema compilation at install)
  - GLib resolves GTimeZone ids from individual TZif files (TZDIR), but
    the OHOS image only ships the Android-style single-file tzdata blob
    (/system/etc/zoneinfo/tzdata) and no /usr/share/zoneinfo. The recipe
    splits the blob into a TZif tree at build time, restores the two
    tzdb link ids the locations DB references (Antarctica/South_Pole,
    Pacific/Johnston), runs the upstream tests with TZDIR pointing at
    it, and packages it as share/zoneinfo for consumers
  - upstream 4 TAP tests (test_libgweather/duplicates/timezones/metar)
    executed on the OHOS host right after the meson build — the conan
    build host IS the OHOS armv8 target device, so the freshly built
    test binaries run natively (same pattern as the consumer test)
  - .so re-signed with binary-sign-tool after install (OHOS loader
    requires a valid .codesign section)
  - upstream test runtime: dependency .so files walked out of the
    dependency packages (independent of cpp_info libdirs), copied to a
    build-dir shadow dir, .codesign-stripped and re-signed, shadow dir
    first on LD_LIBRARY_PATH — registry artifacts can carry signatures
    the device loader rejects and layouts that diverge from declared
    libdirs (official worker PR #15863 exit 127 evidence)
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Libgweather4Conan(ConanFile):
    name = "libgweather-4"
    version = "4.6.0"
    description = "GNOME weather and world-locations library (GWeather)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgweather"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Shared published binary graph — aligned with the official
        # geocode-glib/3.26.4 recipe (libshumate 1.7.0-aligned graph):
        # glib/2.84.0.1.1 + json-glib/1.10.6 + libsoup3/3.6.5-r3 +
        # zlib/1.3.1.1 keep a single GObject copy in the process (the
        # r1-era libsoup statically embedded glib — two GType domains
        # in one process crash g_type_register_static).
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("json-glib/1.10.6")
        self.requires("libsoup3/3.6.5-r3")
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1.1", override=True)
        # 4.6.0 hard requirements delivered by the dependency-first runs
        self.requires("geocode-glib/3.26.4")
        self.requires("gweather-locations/2026.2")

    def generate(self):
        # Cap build parallelism at min(cores, 4): official platform CI workers fail ninja -j20 with "posix_spawn: Resource temporarily unavailable" (worker process limits, PR #15863 log).
        self.conf.define("tools.build:jobs", min(os.cpu_count() or 1, 4))
        tc = MesonToolchain(self)
        tc.project_options["introspection"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["enable_vala"] = "false"
        tc.project_options["tests"] = "true"
        # real tzdata location on the OHOS image (ZONEINFO_DIR is not
        # referenced by 4.6.0 runtime code, kept for correctness)
        tc.project_options["zoneinfo_dir"] = "/system/etc/zoneinfo"
        _llvm_ar = os.path.realpath("/data/service/hnp/bin/llvm-ar")
        if not os.path.isfile(_llvm_ar):
            _llvm_ar = "/data/service/hnp/bin/ar"
        if os.path.isfile(_llvm_ar):
            tc.binaries["ar"] = _llvm_ar
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        _llvm_bin = os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang"))
        if os.path.isdir(_llvm_bin):
            self.buildenv_info.prepend("PATH", _llvm_bin)
        _glib_bin = os.path.join(str(self.dependencies["glib"].package_folder), "bin")
        if os.path.isdir(_glib_bin):
            self.buildenv_info.prepend("PATH", _glib_bin)
        # Runtime data env for consumers (runenv_info aggregates into the
        # consumers' conanrun env). libgweather-4 is the one hop that can
        # see both its own package folder and the (data-only, pruned from
        # consumer graphs) gweather-locations package folder.
        try:
            _gwl = str(self.dependencies["gweather-locations"].package_folder)
            self.runenv_info.define_path("LIBGWEATHER_LOCATIONS_PATH",
                os.path.join(_gwl, "lib", "gweather-locations", "Locations.bin"))
        except KeyError:
            pass
        if self.package_folder:
            _pkg = str(self.package_folder)
            self.runenv_info.define_path("GSETTINGS_SCHEMA_DIR",
                os.path.join(_pkg, "share", "glib-2.0", "schemas"))
            _zi = os.path.join(_pkg, "share", "zoneinfo")
            if os.path.isdir(_zi):
                self.runenv_info.define_path("TZDIR", _zi)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── build-host environment plumbing (geocode-glib precedent) ──

    # tzdb backward links / merges the compact OHOS tzdata blob does not
    # carry (it ships primary zones only): alias ids referenced by the
    # gweather-locations database to their tzdb successor (equivalent
    # rules by definition of the merge/link).
    _TZ_LINKS = {
        "Antarctica/South_Pole": "Antarctica/McMurdo",
        "Pacific/Johnston": "Pacific/Honolulu",
    }

    def _prepare_zoneinfo(self):
        """GLib resolves GTimeZone ids from individual TZif files under
        TZDIR (then /usr/share/zoneinfo etc. — none exist on OHOS). The
        OHOS image only ships the Android-style single-file tzdata blob
        (/system/etc/zoneinfo/tzdata): split it into a per-build TZif
        tree the tests (and downstream consumers, via share/zoneinfo)
        can point TZDIR at. Returns the TZDIR path or None."""
        zi_dir = os.path.join(self.build_folder, "zoneinfo")
        legacy = "/system/etc/zoneinfo"
        blob_path = os.path.join(legacy, "tzdata")
        if os.path.isfile(os.path.join(legacy, "America", "Sao_Paulo")):
            return legacy
        if not os.path.isfile(blob_path):
            self.output.warning("no usable tzdata for GLib GTimeZone resolution")
            return None
        import struct

        with open(blob_path, "rb") as _f:
            blob = _f.read()
        if blob[:6] != b"tzdata":
            self.output.warning("unexpected tzdata blob format, skipping extraction")
            return None
        index_off, data_off, _final_off = struct.unpack_from(">III", blob, 12)
        os.makedirs(zi_dir, exist_ok=True)
        _count = 0
        _pos = index_off
        while _pos + 48 <= data_off:
            _name = blob[_pos:_pos + 40].split(b"\0")[0].decode()
            _off, _len = struct.unpack_from(">II", blob, _pos + 40)
            _pos += 48
            if not _name or _len == 0:
                continue
            _out = os.path.join(zi_dir, _name)
            _dir = os.path.dirname(_out)
            if not os.path.isdir(_dir):
                os.makedirs(_dir, exist_ok=True)
            with open(_out, "wb") as _f:
                _f.write(blob[data_off + _off:data_off + _off + _len])
            _count += 1
        self.output.info("extracted %d TZif zones from the OHOS tzdata blob" % _count)
        for _missing, _target in self._TZ_LINKS.items():
            _dst = os.path.join(zi_dir, _missing)
            _src_tz = os.path.join(zi_dir, _target)
            if not os.path.exists(_dst) and os.path.isfile(_src_tz):
                shutil.copyfile(_src_tz, _dst)
                self.output.info("tz link %s -> %s restored" % (_missing, _target))
        return zi_dir

    def _prepare_env(self):
        env = os.environ
        _ninja = "/storage/Users/currentUser/usr/local/bin/ninja"
        if not os.path.isfile(_ninja):
            _ninja = "/data/service/hnp/bin/ninja"
        if os.path.isfile(_ninja):
            env.setdefault("NINJA", _ninja)
        env["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + env.get("LD_LIBRARY_PATH", ""))
        glib_bin = os.path.join(str(self.dependencies["glib"].package_folder), "bin")
        if os.path.isdir(glib_bin):
            env["PATH"] = glib_bin + os.pathsep + env["PATH"]
        return env

    def _patch_glib_pcs(self):
        """glib module .pc compat + glib tool variables into glib-2.0.pc,
        plus the tool variables appended to an already generated gio-2.0.pc:
        gnome.post_install(glib_compile_schemas: true) resolves
        `glib_compile_schemas` from gio-2.0.pc at configure time, and Conan's
        PkgConfigDeps regenerates that .pc without the custom variables
        (official glib package)."""
        glib_pkg = self.dependencies["glib"].package_folder
        glib_bin = os.path.join(str(glib_pkg), "bin")
        _pcs = []
        for _root in [self.build_folder, os.path.dirname(self.build_folder)]:
            _pcs = glob.glob(os.path.join(_root, "**", "glib-2.0.pc"), recursive=True)
            if _pcs:
                break
        _pc_dir = os.path.dirname(_pcs[0]) if _pcs else self.build_folder
        _gio_vars = ("glib_compile_schemas=%s/glib-compile-schemas\n"
                     "gio_querymodules=%s/gio-querymodules\n"
                     % (glib_bin, glib_bin))
        for _mod in ("gmodule-no-export-2.0", "gobject-2.0", "gio-2.0",
                     "gio-unix-2.0", "gthread-2.0"):
            pc_path = os.path.join(_pc_dir, "%s.pc" % _mod)
            if not os.path.exists(pc_path):
                _lib = _mod.replace("-no-export", "").replace("unix-", "")
                _vars = _gio_vars if _mod == "gio-2.0" else ""
                with open(pc_path, "w") as _f:
                    _f.write(
                        "prefix=%s\n"
                        "libdir=${prefix}/lib\n"
                        "includedir=${prefix}/include/glib-2.0\n"
                        "Name: %s\n"
                        "Description: Conan package: %s (compat)\n"
                        "Version: 2.84.0.1.1\n"
                        "Libs: -L${libdir} -l%s\n"
                        "Cflags: -I${includedir}\n%s"
                        % (glib_pkg, _mod, _mod, _lib, _vars))
                self.output.info("generated compat %s.pc in %s" % (_mod, _pc_dir))
            elif _mod == "gio-2.0":
                with open(pc_path) as _f:
                    _t = _f.read()
                if "glib_compile_schemas" not in _t:
                    with open(pc_path, "a") as _f:
                        _f.write(_gio_vars)
                    self.output.info("patched generated gio-2.0.pc with glib tool vars")
        if _pcs:
            with open(_pcs[0]) as _f:
                _pc_content = _f.read()
            if "glib_mkenums" not in _pc_content:
                with open(_pcs[0], "a") as _f:
                    _f.write(
                        "glib_mkenums=%s/glib-mkenums\n"
                        "glib_compile_resources=%s/glib-compile-resources\n"
                        "glib_genmarshal=%s/glib-genmarshal\n"
                        "glib_compile_schemas=%s/glib-compile-schemas\n"
                        % (glib_bin, glib_bin, glib_bin, glib_bin))
                self.output.info("patched glib-2.0.pc with glib tool vars")

    def _patch_soup_pc(self):
        """libsoup-3.0.pc: add the include/libsoup-3.0 subdir to Cflags."""
        _soup_pc = None
        for _root in [self.build_folder, os.path.dirname(self.build_folder)]:
            _c = glob.glob(os.path.join(_root, "libsoup-3.0.pc"))
            if _c:
                _soup_pc = _c[0]
                break
        if _soup_pc and os.path.isfile(_soup_pc):
            with open(_soup_pc) as _f:
                _t = _f.read()
            if "include/libsoup-3.0" not in _t:
                _t = _t.replace(
                    "Cflags: -I\"${includedir}\"",
                    "Cflags: -I\"${includedir}/libsoup-3.0\" -I\"${includedir}\"", 1)
                with open(_soup_pc, "w") as _f:
                    _f.write(_t)
                self.output.info("libsoup-3.0.pc: appended include/libsoup-3.0 to Cflags")

    def _patch_locations_pc(self):
        """gweather-locations.pc: restore the locations_db/locations_xml/
        locations_dtd pkg-config variables upstream meson reads (Conan's
        generated .pc carries only prefix/lib/include)."""
        _gwl_pc = None
        for _root in [self.build_folder, os.path.dirname(self.build_folder)]:
            _c = glob.glob(os.path.join(_root, "gweather-locations.pc"))
            if _c:
                _gwl_pc = _c[0]
                break
        if _gwl_pc and os.path.isfile(_gwl_pc):
            with open(_gwl_pc) as _f:
                _t = _f.read()
            if "locations_db" not in _t:
                # absolute paths into the gweather-locations package: this
                # generated .pc lives in the ephemeral generators folder
                _gwl_pkg = str(self.dependencies["gweather-locations"].package_folder)
                with open(_gwl_pc, "a") as _f:
                    _f.write(
                        "locations_dtd=%s/share/gweather-locations/locations.dtd\n"
                        "locations_xml=%s/share/gweather-locations/Locations.xml\n"
                        "locations_db=%s/lib/gweather-locations/Locations.bin\n"
                        % (_gwl_pkg, _gwl_pkg, _gwl_pkg))
                self.output.info("patched gweather-locations.pc with locations_db vars")
        else:
            raise ConanException("gweather-locations.pc not found in generators")

    # ── upstream TAP tests, executed on this OHOS host ──

    # Subtrees pruned from dependency package lib scans (no shared libs are
    # shipped there; bounds os.walk cost for oversized packages)
    _WALK_PRUNE = ("include", "share", "bin", "pkgconfig", "cmake", "man",
                   "doc", "licenses", "__pycache__")

    def _collect_libdirs(self):
        dirs = []
        for _name, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base:
                continue
            for _p in (_d.cpp_info.libdirs or []):
                if not os.path.isabs(_p):
                    _p = os.path.join(str(_base), _p)
                if _p not in dirs and os.path.isdir(_p):
                    dirs.append(_p)
        return dirs

    def _prepare_test_libs(self):
        """Test-time dependency lib fallback: copy + re-sign actual .so files.

        Rationale (official worker PR #15863): the TAP phase failed with
        `Error loading shared library libjson-glib-1.0.so.0` exit 127 even
        though the package libdir was on LD_LIBRARY_PATH — the ohpcd
        artifact's .codesign signature is rejected by the OHOS loader
        (reproduced on this device with the identical artifact; selfSign
        re-sign clears it), and artifact lib layouts can also diverge from
        the cpp_info-declared libdirs (componentized packages). So: os.walk
        each dependency package folder, aggregate the directories that
        actually contain .so/.so.* files (independent of declared libdirs),
        copy real .so files into a flat shadow dir, strip .codesign and
        re-sign with binary-sign-tool (same pattern as package()), mirror
        symlink names onto the signed copies, and put the shadow dir first
        on LD_LIBRARY_PATH — test resolution then depends on neither the
        artifact layout nor its signature state. Returns
        (shadow_dir, walked_dirs_with_so).
        """
        shadow = os.path.join(self.build_folder, "test-libs")
        os.makedirs(shadow, exist_ok=True)
        walked_dirs = []
        links = []
        for _name, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base or not os.path.isdir(str(_base)):
                continue
            for _root, _dnames, _fnames in os.walk(str(_base), topdown=True):
                _dnames[:] = [x for x in _dnames if x not in self._WALK_PRUNE]
                _has_so = False
                for _f in _fnames:
                    if not _f.endswith(".so") and ".so." not in _f:
                        continue
                    _src = os.path.join(_root, _f)
                    if os.path.islink(_src):
                        _has_so = True
                        links.append((_f, os.path.basename(os.readlink(_src))))
                        continue
                    if not os.path.isfile(_src):
                        continue
                    with open(_src, "rb") as _fh:
                        if _fh.read(4) != b"\x7fELF":
                            continue  # not a runtime lib (e.g. lib*.so.*.symbols text)
                    _has_so = True
                    _dst = os.path.join(shadow, _f)
                    if os.path.exists(_dst):
                        continue
                    shutil.copy2(_src, _dst)
                    self.run('llvm-objcopy --remove-section=.codesign "%s"'
                             % _dst, ignore_errors=True)
                    self.run('binary-sign-tool sign -inFile "%s" -outFile "%s" '
                             '-selfSign 1' % (_dst, _dst))
                    os.chmod(_dst, 0o755)
                    self.output.info("test-libs: signed copy of %s" % _f)
                if _has_so and _root not in walked_dirs:
                    walked_dirs.append(_root)
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
        return shadow, walked_dirs

    def _run_upstream_tests(self):
        """Run the 4 upstream TAP test executables natively.

        Environment mirrors libgweather/tests/meson.build:
        LIBGWEATHER_LOCATIONS_PATH -> Locations.bin, SCHEMASDIR ->
        source schemas, SCHEMAS_BUILDDIR -> generated enums.xml,
        GSETTINGS_BACKED=memory, GIO_USE_VFS=local; the tests spawn
        glib-compile-schemas themselves (glib package bin is on PATH).
        """
        bash = "/data/service/hnp/bin/bash"
        tests_dir = os.path.join(self.build_folder, "libgweather", "tests")
        loc_bin = os.path.join(
            str(self.dependencies["gweather-locations"].package_folder),
            "lib", "gweather-locations", "Locations.bin")
        if not os.path.isfile(loc_bin):
            raise ConanException("Locations.bin not found: %s" % loc_bin)
        schemas_src = os.path.join(self.source_folder, "schemas")
        schemas_build = os.path.join(self.build_folder, "schemas")
        _shadow, _walked = self._prepare_test_libs()
        _ld = [_shadow]
        for _d in self._collect_libdirs() + _walked:
            if _d not in _ld:
                _ld.append(_d)
        ldpath = os.pathsep.join(_ld)
        _tzdir = self._tzdir if getattr(self, "_tzdir", None) else self._prepare_zoneinfo()
        self._tzdir = _tzdir
        self._gwl_loc_bin = loc_bin
        _tzenv = "TZDIR=%s " % shlex.quote(_tzdir) if _tzdir else ""
        for _t in ("test_libgweather", "duplicates", "timezones", "metar"):
            exe = os.path.join(tests_dir, _t)
            if not os.path.isfile(exe):
                raise ConanException("upstream test binary missing: %s" % exe)
            _extra = "LIBGWEATHER_LOCATIONS_NO_NEAREST=1 " if _t == "duplicates" else ""
            cmd = (
                "export LD_LIBRARY_PATH=\"{ld}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
                "env {tz}LIBGWEATHER_LOCATIONS_PATH={loc} SCHEMASDIR={ssrc} "
                "SCHEMAS_BUILDDIR={sbld} GSETTINGS_BACKED=memory GIO_USE_VFS=local "
                "{extra}{exe} --tap -k"
            ).format(ld=ldpath, tz=_tzenv, loc=shlex.quote(loc_bin),
                     ssrc=shlex.quote(schemas_src), sbld=shlex.quote(schemas_build),
                     extra=_extra, exe=shlex.quote(exe))
            self.output.info("upstream TAP test %s:" % _t)
            ret = self.run("%s -c '%s'" % (bash, cmd), ignore_errors=True)
            if ret != 0:
                raise ConanException("upstream test %s failed (exit %d)" % (_t, ret))
            self.output.info("upstream TAP test %s: PASS" % _t)

    def build(self):
        self._prepare_env()
        apply_conandata_patches(self)
        self._patch_glib_pcs()
        self._patch_soup_pc()
        self._patch_locations_pc()
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def package(self):
        self._prepare_env()
        meson = Meson(self)
        meson.install()
        # gnome.post_install(glib_compile_schemas) is skipped by meson
        # whenever DESTDIR is set (conan staged installs always set it);
        # compile the schemas into the package explicitly.
        _schemas_dir = os.path.join(str(self.package_folder),
                                    "share", "glib-2.0", "schemas")
        if os.path.isdir(_schemas_dir) and not os.path.isfile(
                os.path.join(_schemas_dir, "gschemas.compiled")):
            _gcs_src = os.path.join(
                str(self.dependencies["glib"].package_folder),
                "bin", "glib-compile-schemas")
            if os.path.isfile(_gcs_src):
                # Registry-delivered glib tools can carry codesign sections
                # the local OHOS loader rejects (exec fails with
                # "Operation not permitted", CI run4). Re-sign a local copy
                # (same binary-sign-tool pattern as the .so re-sign below)
                # and run it with the graph libdirs on LD_LIBRARY_PATH
                # (same pattern as the upstream TAP runs).
                _gcs = os.path.join(self.build_folder, "glib-compile-schemas")
                shutil.copyfile(_gcs_src, _gcs)
                os.chmod(_gcs, 0o755)
                self.run('binary-sign-tool sign -inFile "%s" -outFile "%s" '
                         '-selfSign 1' % (_gcs, _gcs), ignore_errors=True)
                os.chmod(_gcs, 0o755)
                self.run('env LD_LIBRARY_PATH="%s" "%s" "%s"'
                         % (os.pathsep.join(self._collect_libdirs()),
                            _gcs, _schemas_dir))
                self.output.info("compiled GSettings schemas (meson skips "
                                 "post_install under DESTDIR)")
        # Ship the GLib-usable TZif tree (extracted from the OHOS tzdata
        # blob) so consumers can point TZDIR at <pkg>/share/zoneinfo.
        _tzdir = self._tzdir if getattr(self, "_tzdir", None) else self._prepare_zoneinfo()
        self._tzdir = _tzdir
        if _tzdir and os.path.isdir(_tzdir):
            _dest = os.path.join(str(self.package_folder), "share", "zoneinfo")
            if not os.path.isdir(_dest):
                shutil.copytree(_tzdir, _dest)
                self.output.info("packaged GLib-usable zoneinfo tree at share/zoneinfo")
        # Ship the runtime data env (Locations.bin path from the
        # gweather-locations package, schema dir and TZDIR inside this
        # package) so consumers can source it — env piping through the
        # conan graph is unreliable on this host (empty conanrun.sh).
        _loc_bin = getattr(self, "_gwl_loc_bin", None)
        if not _loc_bin:
            try:
                _loc_bin = os.path.join(
                    str(self.dependencies["gweather-locations"].package_folder),
                    "lib", "gweather-locations", "Locations.bin")
            except KeyError:
                _loc_bin = None
        if _loc_bin and os.path.isfile(_loc_bin):
            _env_dir = os.path.join(str(self.package_folder), "share", "gweather-4")
            if not os.path.isdir(_env_dir):
                os.makedirs(_env_dir, exist_ok=True)
            with open(os.path.join(_env_dir, "runtime-env.sh"), "w") as _f:
                _f.write("# runtime data env for gweather4 consumers (source me)\n")
                _f.write("LIBGWEATHER_LOCATIONS_PATH=%s\n" % shlex.quote(_loc_bin))
                _f.write("GSETTINGS_SCHEMA_DIR=%s\n" % shlex.quote(os.path.join(
                    str(self.package_folder), "share", "glib-2.0", "schemas")))
                if _tzdir and os.path.isdir(_tzdir):
                    _f.write("TZDIR=%s\n" % shlex.quote(os.path.join(
                        str(self.package_folder), "share", "zoneinfo")))
            self.output.info("wrote share/gweather-4/runtime-env.sh")
        # Re-sign the shared library (OHOS loader requires .codesign).
        for _so in glob.glob(os.path.join(self.package_folder, "lib", "libgweather-4.so*")):
            if os.path.isfile(_so) and not os.path.islink(_so):
                self.run('llvm-objcopy --remove-section=.codesign "%s"' % _so,
                         ignore_errors=True)
                self.run('binary-sign-tool sign -inFile "%s" -outFile "%s" -selfSign 1'
                         % (_so, _so))
                self.output.info("re-signed %s" % os.path.basename(_so))

    def package_info(self):
        self.cpp_info.libs = ["gweather-4"]
        self.cpp_info.set_property("pkg_config_name", "gweather4")
        self.cpp_info.set_property("cmake_file_name", "gweather4")
        self.cpp_info.set_property("cmake_target_name", "gweather4::gweather4")
        # Headers install to include/libgweather-4.0/libgweather/*.h and
        # consumers do #include <libgweather/gweather.h> — include base is
        # one level up from the header dir (geocode-glib precedent).
        self.cpp_info.includedirs = ["include/libgweather-4.0"]
