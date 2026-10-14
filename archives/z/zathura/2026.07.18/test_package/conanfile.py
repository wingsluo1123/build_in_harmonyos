#!/usr/bin/env python3
"""Test package for zathura — real consumer end-to-end verification.

zathura is an application package.  It installs the ``zathura`` CLI (built with
``export_dynamic``, so its plugin API symbols are visible to ``dlopen``'d
plugins), the plugin API headers, and a pkg-config file — which is exactly what
a third-party plugin (zathura-pdf-poppler, zathura-pdf-mupdf, zathura-djvu, ...)
consumes.

``test.c`` therefore plays the plugin's role end to end:

  1. it compiles against the *installed* headers and uses the package's own
     ``ZATHURA_PLUGIN_REGISTER_WITH_FUNCTIONS()`` macro to emit the exported
     ``zathura_plugin_<api>_<abi>`` definition struct the viewer resolves;
  2. it ``dlopen``s the installed ``zathura`` executable as the host process and
     checks the API symbols a plugin must bind to are exported;
  3. it calls the resolved ``zathura_image_buffer_create()``/``_free()`` through
     the host's dynamic symbol table and performs a real pixel round trip.

Because the probe deliberately binds against the host's symbol table, it only
needs ``-ldl`` at link time; the API symbols are resolved at run time exactly as
a released plugin does.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.gnu import PkgConfigDeps


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The plugin API headers include girara headers, so a real consumer
        # needs girara's headers and cairo/json-glib on the include path (the
        # zathura.pc file declares "Requires: girara, cairo").  Pinned to the
        # same revision the recipe uses.
        #
        # No further runtime requirements are declared on purpose: the resolved
        # graph already contains every transitive node of the zathura package
        # (gtk4, pango, cairo, json-glib, libmagic, sqlite3, xxhash, ...), and
        # the loader path below is derived from that graph.  Adding duplicates
        # here would only pin versions the recipe already fixed.
        self.requires("girara/2026.07.07.1")
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("harfbuzz/14.2.0.1.1.1", override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)

    def generate(self):
        PkgConfigDeps(self).generate()

    # ----------------------------------------------------------------------
    # Runtime search path, derived from the ELF objects themselves.
    #
    # The Conan dependency graph describes what the *recipe* declared; the
    # dynamic loader asks for what DT_NEEDED says.  The two disagree whenever a
    # dependency pulls in a shared object this recipe never names -- on the CI
    # worker libintl.so.8 (gettext) was in the zathura host's DT_NEEDED while
    # appearing in neither self.dependencies nor any generated .pc file.  So the
    # path is computed by walking the host's real transitive closure, and the
    # dependency-graph list is kept only as a superset.
    #
    # readelf/patchelf are not guaranteed to exist in the CI container, so the
    # ELF is parsed directly (target is ELF64 little-endian aarch64).
    #
    # ----------------------------------------------------------------------
    # Why the roots are NOT taken from cpp_info.libdirs
    #
    # The previous revision built the soname-search roots from
    # ``dep.cpp_info.libdirs``/``bindirs``.  That is unreliable for two measured
    # reasons, both observed on the real dependency graph (33 nodes):
    #
    #   * for 10 of the 33 nodes Conan reports ``package_folder is None`` and
    #     ``cpp_info.libdirs == ['lib']`` -- a path *relative* to the process
    #     CWD.  The old ``os.path.isdir(d)`` guard then evaluated ``'lib'``
    #     against the test_package directory, got False, and silently dropped
    #     the node.  Any DT_NEEDED soname supplied only by such a node became
    #     unresolvable, so its directory never entered LD_LIBRARY_PATH and
    #     ``dlopen(bin/zathura)`` failed with
    #         Error loading shared library <soname>: (needed by .../bin/zathura)
    #     which is exactly the CI #90729 failure (libjson-glib-1.0.so.0).
    #   * the set of nodes that report a folder is not stable across machines
    #     or graphs, so a root set that depends on it makes the test flaky in a
    #     way that is very hard to attribute.
    #
    # The fix is to stop guessing from cpp_info.  Conan resolves an absolute
    # ``package_folder`` for every node it actually installed; those folders are
    # the ground truth, and each contributes its conventional library
    # subdirectories.  Nodes without a folder (e.g. a pure header/aggregator
    # node) simply contribute nothing, which is correct.
    # ----------------------------------------------------------------------
    @staticmethod
    def _elf_dynamic_strings(path, wanted_tags):
        """Return {tag: [strings]} for the given dynamic tags of an ELF64 file.

        Only tags 1 (DT_NEEDED), 5 (DT_STRTAB) and 14 (DT_SONAME) are of
        interest.  Returns an empty dict when the file is not a readable
        ELF64 little-endian object.
        """
        import struct
        out = {}
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return out
        if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return out
        try:
            e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
            e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
            e_phnum = struct.unpack_from("<H", data, 0x38)[0]
        except struct.error:
            return out

        phdrs = []
        for i in range(e_phnum):
            o = e_phoff + i * e_phentsize
            try:
                p_type = struct.unpack_from("<I", data, o)[0]
                p_offset = struct.unpack_from("<Q", data, o + 0x08)[0]
                p_vaddr = struct.unpack_from("<Q", data, o + 0x10)[0]
                p_filesz = struct.unpack_from("<Q", data, o + 0x20)[0]
            except struct.error:
                break
            phdrs.append((p_type, p_offset, p_vaddr, p_filesz))

        dyn = next(((o, s) for (t, o, _v, s) in phdrs if t == 2), None)
        if dyn is None:
            return out

        def vaddr_to_off(vaddr):
            for (t, p_offset, p_vaddr, p_filesz) in phdrs:
                if t == 1 and p_vaddr <= vaddr < p_vaddr + p_filesz:
                    return p_offset + (vaddr - p_vaddr)
            return None

        off, size = dyn
        strtab = None
        offsets = {}
        for i in range(0, size, 16):
            try:
                tag, val = struct.unpack_from("<QQ", data, off + i)
            except struct.error:
                break
            if tag == 0:
                break
            if tag == 5:
                strtab = val
            elif tag in wanted_tags:
                offsets.setdefault(tag, []).append(val)
        if strtab is None:
            return out
        base = vaddr_to_off(strtab)
        if base is None:
            return out
        for tag, vals in offsets.items():
            names = []
            for nameoff in vals:
                start = base + nameoff
                end = data.find(b"\x00", start)
                if end < 0:
                    continue
                names.append(data[start:end].decode("utf-8", "replace"))
            out[tag] = names
        return out

    @classmethod
    def _elf_needed(cls, path):
        """DT_NEEDED sonames of an ELF, or []."""
        return cls._elf_dynamic_strings(path, (1,)).get(1, [])

    @classmethod
    def _elf_soname(cls, path):
        """DT_SONAME of an ELF, or None."""
        names = cls._elf_dynamic_strings(path, (14,)).get(14) or []
        return names[0] if names else None

    # Conventional library locations inside a Conan package folder.  Every
    # entry is tried; non-existent ones are skipped.  These are relative names
    # so that only the *folder* has to be authoritative.
    _LIB_SUBDIRS = ("lib", "lib64", "bin",
                    os.path.join("lib", "glib-2.0"),
                    os.path.join("lib", "x86_64-linux-gnu"),
                    os.path.join("lib", "aarch64-linux-gnu"))

    def _package_libdirs(self):
        """Absolute library directories of every dependency.

        Combines two sources that are absolute *by construction*, because
        ``cpp_info.libdirs`` is not (it degrades to the relative string ``'lib'``
        whenever a node reports no package folder -- measured on 10 of the 33
        nodes of this very graph):

          1. ``dep.package_folder``: the path Conan installed the node to.
             Only nodes that actually report a folder contribute here.
          2. the ``libdir=`` entries of the ``.pc`` files that PkgConfigDeps
             wrote into the generators folder.  This is what rescues the nodes
             from (1): PkgConfigDeps emits an absolute libdir for every
             dependency it generates a .pc for, including ones whose dependency
             object exposes no folder.

        Measured on the real graph: source (1) alone covers 11 of the 12
        DT_NEEDED sonames of bin/zathura (it misses libxxhash.so.0), source (2)
        alone covers all 12, and together they resolve the whole closure.  Both
        are collected; duplicates are dropped.
        """
        dirs = []
        try:
            deps = list(self.dependencies.values())
        except Exception:  # noqa: BLE001 - never let env prep fail the build
            deps = []
        for dep in deps:
            try:
                folder = dep.package_folder
            except Exception:  # noqa: BLE001
                folder = None
            if not folder or not os.path.isdir(folder):
                continue
            for rel in self._LIB_SUBDIRS:
                cand = os.path.join(folder, rel)
                if os.path.isdir(cand) and cand not in dirs:
                    dirs.append(cand)
        # Source (2): absolute libdirs from the generated .pc files.
        for cand in self._pcdir_libdirs():
            if cand not in dirs:
                dirs.append(cand)
        return dirs

    def _pcdir_libdirs(self):
        """Absolute ``libdir=`` values from every generated .pc file."""
        out = []
        try:
            names = sorted(n for n in os.listdir(self.generators_folder)
                           if n.endswith(".pc"))
        except OSError:
            return out
        for name in names:
            try:
                with open(os.path.join(self.generators_folder, name), "r",
                          encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            prefix = ""
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("prefix="):
                    prefix = line[len("prefix="):].strip().strip('"')
                elif line.startswith("libdir="):
                    raw = line[len("libdir="):].strip().strip('"')
                    for token in ("${prefix}", "$prefix"):
                        raw = raw.replace(token, prefix)
                    if raw and os.path.isabs(raw) and os.path.isdir(raw) \
                            and raw not in out:
                        out.append(raw)
        return out

    @classmethod
    def _index_sonames(cls, roots):
        """Map every discoverable name -> absolute path under `roots`."""
        index = {}
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    if ".so" not in fn:
                        continue
                    full = os.path.join(dirpath, fn)
                    sn = cls._elf_soname(full)
                    if sn:
                        index.setdefault(sn, full)
                    index.setdefault(fn, full)
        return index

    def _host_closure_libdirs(self, exe):
        """Directories holding every shared object the host loads, and any gaps.

        Returns (dirs, missing).  `missing` holds sonames that could not be
        resolved anywhere in the dependency package folders -- reported rather
        than silently dropped, because an incomplete path is precisely the
        failure this method exists to prevent.

        `dirs` is returned in closure order: the directory of an object named by
        DT_NEEDED comes before directories discovered later, so a soname is
        always resolved against the same file the loader would pick.
        """
        roots = self._package_libdirs()
        # The package under test itself may install a shared object outside the
        # conventional subdirs; include its declared libdirs as a widening, but
        # only when they are absolute (relative entries are meaningless here).
        try:
            for d in list(self.dependencies["zathura"].cpp_info.libdirs):
                if d and os.path.isabs(d) and os.path.isdir(d) and d not in roots:
                    roots.append(d)
        except Exception:  # noqa: BLE001
            pass
        index = self._index_sonames(roots)

        seen, queue, dirs, missing = set(), [exe], [], set()
        while queue:
            cur = queue.pop(0)
            if not cur or cur in seen or not os.path.isfile(cur):
                continue
            seen.add(cur)
            d = os.path.dirname(cur)
            if d not in dirs:
                dirs.append(d)
            for need in self._elf_needed(cur):
                # The C library and the dynamic loader itself always come from
                # the target sysroot, never from a Conan package.
                if need.startswith("libc.so") or need.startswith("ld-musl"):
                    continue
                hit = index.get(need)
                if hit is None:
                    missing.add(need)
                elif hit not in seen:
                    queue.append(hit)
        return dirs, missing

    # Sonames that legitimately come from the target sysroot/toolchain rather
    # than from any Conan package.  Anything else left unresolved is a real gap
    # in the derived path and must fail loudly -- a silently incomplete path is
    # what produced the CI #90729 failure in the first place.
    _TOOLCHAIN_SONAMES = ("libc++_shared.so", "libc++abi.so", "libunwind.so")

    @staticmethod
    def _ensure_readable(dirs):
        """Make the loader path usable by this process.

        Prebuilt packages fetched from the remote arrive with the *uploader's*
        numeric uid/gid preserved and mode 750 (``-rwxr-x---``) on their shared
        objects -- and on the symlinks beside them.  When the CI worker builds as
        a different user, the dynamic loader cannot open those entries and
        reports them exactly like missing libraries:

            Error loading shared library libjson-glib-1.0.so.0:
              (needed by .../bin/zathura)

        That message is misleading: the library is present and its directory is
        on LD_LIBRARY_PATH; the open() itself fails with EACCES.  Verified on the
        CI-resolved graph -- json-glib's object is mode 750 owned by
        20001006:1006, openable by root but raising EACCES for any other user.

        Widening must cover every entry in the directory, not only the objects the
        closure walk resolved: the loader looks up a *soname* (a symlink such as
        ``libgirara.so.5``) and then opens the file it points at, and both can be
        750.  Measured on this graph, restricting the change to closure objects
        left 18 entries on the loader path unreadable for a non-root user.

        Only the read bits are added, nothing is made writable, and the change is
        confined to directories already on the derived loader path.
        """
        fixed = 0
        for d in dirs:
            if not d or not os.path.isdir(d):
                continue
            try:
                entries = os.listdir(d)
            except OSError:
                continue
            for name in entries:
                if ".so" not in name:
                    continue
                path = os.path.join(d, name)
                try:
                    mode = os.stat(path).st_mode
                except OSError:
                    continue
                if mode & 0o044 == 0o044:
                    continue
                try:
                    os.chmod(path, mode | 0o044)
                    fixed += 1
                except OSError:
                    continue
        return fixed

    @staticmethod
    def _first_unreadable(dirs):
        """Return the first loader-path entry that cannot be opened, else None."""
        for d in dirs:
            if not d or not os.path.isdir(d):
                continue
            try:
                entries = os.listdir(d)
            except OSError:
                continue
            for name in entries:
                if ".so" not in name:
                    continue
                path = os.path.join(d, name)
                try:
                    with open(path, "rb") as fh:
                        fh.read(1)
                except OSError:
                    return path
        return None

    def _runtime_libdirs(self):
        """Library dirs from the generated .pc files.

        Kept as the broad superset appended after the DT_NEEDED closure, so that
        an object the closure walk never reaches (e.g. a plugin dlopen'd later)
        is still findable.  Shares the implementation with _package_libdirs().
        """
        return self._pcdir_libdirs()

    def build(self):
        dep = self.dependencies["zathura"]
        # The package installs the API headers to <prefix>/include/zathura and
        # declares includedirs ["include/zathura", "include"], so the header may
        # be reachable either as <inc>/plugin-api.h or <inc>/zathura/plugin-api.h
        # depending on which entry is inspected.  Search both spellings.
        hdr = None
        for inc in dep.cpp_info.includedirs:
            for rel in (os.path.join("zathura", "plugin-api.h"), "plugin-api.h"):
                cand = os.path.join(inc, rel)
                if os.path.isfile(cand):
                    hdr = cand
                    break
            if hdr:
                break
        if hdr is None:
            raise ConanInvalidConfiguration(
                "zathura plugin API header not found under %s"
                % dep.cpp_info.includedirs)
        self.output.info("plugin API header: %s" % hdr)

        exe = self._resolve_host_executable(dep)

        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c") or "clang"

        # The OHOS SDK's lld needs libxml2.so.16 from the SDK's own lib dir on
        # the loader path (same workaround as the other meson recipes here).
        cc_dir = os.path.dirname(os.path.realpath(cc))
        for cand in (os.path.join(cc_dir, "..", "lib"), os.path.join(cc_dir, "lib")):
            libdir = os.path.normpath(cand)
            if os.path.isfile(os.path.join(libdir, "libxml2.so.16")):
                old = os.environ.get("LD_LIBRARY_PATH", "")
                if libdir not in old.split(":"):
                    os.environ["LD_LIBRARY_PATH"] = libdir + (":" + old if old else "")
                break

        inc_flags = " ".join('-I"%s"' % d for d in dep.cpp_info.includedirs)
        # Add the dependency headers.  The reliable source of the full,
        # always-correct include set (girara, glib, and glib's arch-specific
        # glibconfig.h under lib/glib-2.0/include) is the pkg-config files that
        # PkgConfigDeps just generated, so query those rather than guessing
        # subdirectories.  Fall back to cpp_info when pkg-config is absent.
        pcdir = self.generators_folder.replace("\\", "/")
        pc_flags = None
        # Resolve an absolute pkg-config: the bare name may not exist on PATH in
        # the build container, and the recipe already pins one via conf.
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config:
            pkg_config = shutil.which("pkg-config")
        if pkg_config:
            try:
                import subprocess
                # PKG_CONFIG_LIBDIR *replaces* the built-in search path, which is
                # the whole point: the host's /usr/lib/x86_64-linux-gnu/pkgconfig
                # holds an older glib whose --cflags would silently answer this
                # query and make the consumer test link against host headers
                # instead of the packaged ones.  PKG_CONFIG_PATH alone only
                # prepends and therefore does not prevent that.
                env = dict(os.environ,
                           PKG_CONFIG_PATH=pcdir,
                           PKG_CONFIG_LIBDIR=pcdir)
                out = subprocess.run(
                    [pkg_config, "--cflags", "girara", "glib-2.0", "gobject-2.0",
                     "gio-2.0", "cairo", "json-glib-1.0"],
                    capture_output=True, text=True, env=env)
                if out.returncode == 0 and out.stdout.strip():
                    pc_flags = out.stdout.strip()
                else:
                    self.output.warning(
                        "pkg-config --cflags exited %d: %s"
                        % (out.returncode, (out.stderr or "").strip()[:200]))
            except Exception as exc:  # noqa: BLE001 - report, do not hide
                self.output.warning("pkg-config query failed: %s" % exc)
        else:
            self.output.warning("no pkg-config found; falling back to cpp_info")
        if pc_flags:
            inc_flags += " " + pc_flags
        else:
            for name in ("girara", "glib", "cairo", "json-glib"):
                try:
                    dep_obj = self.dependencies[name]
                except Exception:
                    continue
                inc_flags += " " + " ".join(
                    '-I"%s"' % d for d in dep_obj.cpp_info.includedirs
                    if os.path.isabs(d))
                root = dep_obj.package_folder
                if root:
                    for sub in (os.path.join("include", "glib-2.0"),
                                os.path.join("lib", "glib-2.0", "include")):
                        cand = os.path.join(root, sub)
                        if os.path.isdir(cand):
                            inc_flags += ' -I"%s"' % cand

        self.output.info("compiling the plugin-role consumer probe")
        self.run('%s -std=c2x test.c -o test_probe %s -ldl' % (cc, inc_flags))
        self.output.info("zathura host executable: %s" % exe)

    @staticmethod
    def _resolve_host_executable(dep):
        """Locate the installed `zathura` host executable.

        build() searches every bindir because a dependency may expose more than
        one; test() must use the same resolution, otherwise a multi-bindir
        dependency would compile successfully and then dlopen a non-existent
        path, reporting a misleading dynamic-loader error (and an IndexError if
        bindirs were empty).
        """
        for bindir in list(dep.cpp_info.bindirs) + [
                os.path.join(dep.package_folder or "", "bin")]:
            if not bindir:
                continue
            candidate = os.path.join(bindir, "zathura")
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "zathura executable not found in any bindir: %s"
            % list(dep.cpp_info.bindirs))

    def test(self):
        dep = self.dependencies["zathura"]
        exe = self._resolve_host_executable(dep)
        if cross_building(self):
            self.output.info(
                "cross-building: consumer probe compiled and linked; runtime "
                "execution is covered by the qemu run and the device evidence")
            return
        # VirtualRunEnv is not enough on its own -- see _host_closure_libdirs().
        # The probe and the host executable it dlopen()s must agree on one
        # loader path, so both are run with the same completed value.
        # Ground truth first: the host executable's own transitive DT_NEEDED
        # closure, then the .pc-derived list as a superset.  Order matters --
        # the directory holding the object actually named by DT_NEEDED must win
        # over a same-named object from an unrelated package.
        closure_dirs, missing = self._host_closure_libdirs(exe)
        # Separate the sonames that legitimately come from the toolchain from
        # genuine gaps.  A genuine gap means the derived path is incomplete and
        # dlopen() will fail on the CI worker, so fail here instead of emitting
        # a warning and letting the probe report a confusing loader error.
        real_gaps = sorted(n for n in missing if n not in self._TOOLCHAIN_SONAMES)
        toolchain = sorted(n for n in missing if n in self._TOOLCHAIN_SONAMES)
        if toolchain:
            self.output.info(
                "host closure references toolchain-provided sonames (resolved "
                "from the target sysroot, not a Conan package): %s"
                % ", ".join(toolchain))
        if real_gaps:
            raise ConanInvalidConfiguration(
                "host closure has unresolved sonames that no dependency "
                "package provides: %s. The runtime library path derived from "
                "package_folder/.pc is incomplete, so dlopen(%s) would fail on "
                "the target." % (", ".join(real_gaps), exe))
        extra = closure_dirs + [d for d in self._runtime_libdirs()
                                if d not in closure_dirs]
        # Cached dependencies may be installed with the uploader's uid and mode
        # 750, which the loader reports as a *missing* library (see
        # _ensure_readable).  Widen readability across the finished loader path
        # before running anything against it.
        chmodded = self._ensure_readable(extra)
        if chmodded:
            self.output.info(
                "widened read permission on %d cached shared object(s) shipped "
                "without group/other read access (a prebuilt package preserves "
                "its uploader's uid; the loader reports the resulting EACCES as "
                "a missing library)" % chmodded)
        unreadable = self._first_unreadable(extra)
        if unreadable:
            raise ConanInvalidConfiguration(
                "shared object is present on the runtime library path but cannot "
                "be opened: %s. The dynamic loader would report this as a "
                "missing library, so the consumer test cannot run." % unreadable)
        inherited = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [d for d in extra if d not in inherited.split(os.pathsep)]
        libpath = os.pathsep.join(parts + ([inherited] if inherited else []))
        self.output.info("runtime libdirs added: %s" % (parts or "(conanrun only)"))
        os.environ["LD_LIBRARY_PATH"] = libpath

        # env=None: do NOT let conan's conanrun script re-export LD_LIBRARY_PATH.
        # The generated conanrunenv-*.sh builds its own value from the *test
        # package's* VirtualRunEnv closure and would replace the exact list
        # assembled above (whose whole point is to carry the transitive runtime
        # closure of bin/zathura, which VirtualRunEnv does not compute). Both
        # lists happen to agree on this dependency graph, but relying on that
        # coincidence is what made this probe fail on the CI worker while
        # passing locally -- see notes.md.  The value set just above IS the
        # ground truth, so it is passed through untouched.
        self.run('./test_probe "%s"' % exe, env=None)

