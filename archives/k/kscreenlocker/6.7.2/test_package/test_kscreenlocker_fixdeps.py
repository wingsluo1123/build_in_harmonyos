#!/usr/bin/env python3
"""Satisfy path-carrying DT_NEEDED entries of the runtime library closure.

The published KF6 dependency libraries were built on a machine whose Conan
home was <HOME>/.cache/conan2 and several of them carry machine-private
DT_NEEDED entries: absolute paths into the publisher's build folders (e.g.
/storage/Users/currentUser/.cache/conan2/p/b/kconf<hash>/p/lib/libKF6ConfigWidgets.so)
or build-tree-relative paths (../../bin/libKF6ConfigCore.so, handled by the
compat bin directory staging in the test_package).  An absolute DT_NEEDED
entry is opened literally by the loader -- no search path applies -- so on
any worker where the publisher's build folder does not exist the whole
process dies at load time ("cannot open shared object file", before main()).
That is the same class of registry hygiene problem the E537 compat bin
stages for; this script extends the staging to absolute entries.

It scans every directory of LD_LIBRARY_PATH (the Conan dependency lib dirs,
exported by the test_package) plus the compat bin directory, builds a
basename -> library map, reads each library's PT_DYNAMIC DT_NEEDED list and
materializes each missing path-carrying entry at its literal path by copying
the matching basename library there (copies, not symlinks -- OHOS /storage
forbids symlinks).  Entries that already exist are left untouched.

Only entries shaped like a Conan cache package path are materialized: after
posixpath.normpath collapsing, the path must contain a /.conan2/p/ or
/.cache/conan2/p/ segment and its basename must start with "lib".  The
marker is deliberately not anchored to this machine's own Conan roots: the
baked-in paths point at the *publisher's* home, and rebuilding that literal
layout here is exactly the point of the staging.  The check runs on the
collapsed value and the copy target is that same collapsed value -- ".."
cannot smuggle an entry past the marker check, and nothing is ever written
to the raw, un-collapsed string.  Anything that fails the shape check is
reported and skipped: writes are confined to lib* files below a cache-shaped
prefix, so package metadata can park files only inside a Conan cache layout
(a pre-existing symlink below a matching prefix aside, which already
requires write access there).

Usage: python3 test_kscreenlocker_fixdeps.py <compat_bin_dir>

Exit status 0 even when entries cannot be satisfied (a warning is printed);
the test run itself remains the acceptance gate.
"""

import os
import posixpath
import shutil
import struct
import sys

E_PHOFF_OFFSET = 0x20
E_PHENTSIZE_OFFSET = 0x36
E_PHNUM_OFFSET = 0x38
PT_LOAD = 1
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5

# The path-carrying entries observed in the published KF6 libraries are
# machine-private absolute paths into the publisher's Conan cache, e.g.
# /storage/Users/currentUser/.cache/conan2/p/b/<id>/p/lib/libKF6ConfigWidgets.so
# (legacy .cache/conan2 layout) or <home>/.conan2/p/<id>/p/lib/... (modern
# layout).  Both carry a p/ package segment right before the lib/ directory.
CACHE_MARKERS = ("/.cache/conan2/p/", "/.conan2/p/")


def _cache_entry_target(entry):
    """Return the normalized write target for a cache-shaped entry, else None.

    DT_NEEDED strings are POSIX paths by definition (ELF), so the
    normalization uses posixpath -- never os.path, which would rewrite
    the separators when the helper is exercised on a non-POSIX host.
    normpath collapses any ".." components first, so a crafted value
    cannot escape the marker check by traversal.  The caller writes to
    the returned value, not to `entry`, so the checked string and the
    written string are always identical.

    The accepted shape is deliberately narrow: a Conan cache package
    segment (see CACHE_MARKERS) plus a "lib"-prefixed basename, so the
    helper only ever creates lib* files inside a cache-shaped layout.
    """
    norm = posixpath.normpath(entry)
    if not any(marker in norm for marker in CACHE_MARKERS):
        return None
    if not posixpath.basename(norm).startswith("lib"):
        return None
    return norm


def _dyn_needed(path):
    """Return the DT_NEEDED strings of an ELF64 file, or None if unreadable."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
        return None
    try:
        e_phoff, = struct.unpack_from("<Q", data, E_PHOFF_OFFSET)
        e_phentsize, = struct.unpack_from("<H", data, E_PHENTSIZE_OFFSET)
        e_phnum, = struct.unpack_from("<H", data, E_PHNUM_OFFSET)
        loads = []
        dyn_off = dyn_sz = None
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type, = struct.unpack_from("<I", data, off)
            p_offset, = struct.unpack_from("<Q", data, off + 8)
            p_vaddr, = struct.unpack_from("<Q", data, off + 16)
            p_filesz, = struct.unpack_from("<Q", data, off + 32)
            if p_type == PT_LOAD:
                loads.append((p_vaddr, p_offset, p_filesz))
            elif p_type == PT_DYNAMIC:
                dyn_off, dyn_sz = p_offset, p_filesz
        if dyn_off is None:
            return None

        def vaddr_to_off(vaddr):
            for seg_vaddr, seg_off, seg_size in loads:
                if seg_vaddr <= vaddr < seg_vaddr + seg_size:
                    return seg_off + (vaddr - seg_vaddr)
            return None

        strtab = None
        needed_offsets = []
        for step in range(dyn_sz // 16):
            tag, val = struct.unpack_from("<qQ", data, dyn_off + step * 16)
            if tag == DT_NULL:
                break
            if tag == DT_STRTAB:
                strtab = vaddr_to_off(val)
            elif tag == DT_NEEDED:
                needed_offsets.append(val)
        if strtab is None:
            return None
        out = []
        for off in needed_offsets:
            start = strtab + off
            end = data.index(b"\0", start)
            out.append(data[start:end].decode("utf-8", "replace"))
        return out
    except (OSError, struct.error, ValueError) as exc:
        # Parse failure (bad e_phoff/e_phnum, truncated dynamic section,
        # unterminated string): report it instead of silently skipping the
        # library -- its DT_NEEDED entries would otherwise never be
        # materialized and the load-time failure would mask the parse bug.
        print("[fixdeps] WARNING: cannot parse %s: %s" % (path, exc))
        return None


def main():
    compat_bin = sys.argv[1] if len(sys.argv) > 1 else ""
    dirs = [d for d in (os.environ.get("LD_LIBRARY_PATH") or "").split(":") if d]
    if compat_bin:
        dirs.append(compat_bin)

    # basename -> first existing library file across the runtime dirs
    by_name = {}
    libs = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".so"):
                continue
            full = os.path.join(d, name)
            if not os.path.isfile(full):
                continue
            by_name.setdefault(name, full)
            libs.append(full)

    fixed, missing, rejected, checked = [], [], [], 0
    for lib in libs:
        needed = _dyn_needed(lib)
        if not needed:
            continue
        checked += 1
        for entry in needed:
            if not entry.startswith("/"):
                # Bare basenames resolve via LD_LIBRARY_PATH; relative
                # entries (../../bin/...) are staged by the compat bin
                # directory in the test_package and resolve against the
                # *test process* CWD, which this helper does not share
                # -- leave them alone.
                continue
            if os.path.exists(entry):
                continue
            target = _cache_entry_target(entry)
            if target is None:
                rejected.append((lib, entry))
                continue
            if os.path.exists(target):
                continue
            basename = target.rsplit("/", 1)[-1]
            source = by_name.get(basename)
            if not source:
                missing.append((lib, entry))
                continue
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(source, target)
                fixed.append((basename, target))
            except OSError as exc:
                missing.append((lib, entry + " (%s)" % exc))

    print("[fixdeps] scanned %d runtime libraries" % checked)
    for basename, entry in fixed:
        print("[fixdeps] staged %s -> %s" % (basename, entry))
    for lib, entry in missing:
        print("[fixdeps] WARNING: no provider for %s (needed by %s)"
              % (entry, lib))
    for lib, entry in rejected:
        print("[fixdeps] WARNING: refusing to materialize %s (needed by %s): "
              "not a Conan cache path" % (entry, lib))
    if not fixed and not missing and not rejected:
        print("[fixdeps] no path-carrying DT_NEEDED entries found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
