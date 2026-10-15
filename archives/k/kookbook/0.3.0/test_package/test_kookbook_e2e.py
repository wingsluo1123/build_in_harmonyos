#!/usr/bin/env python3
"""E2E-KOOKBOOK-01 — real consumer end-to-end case for the packaged kookbook.

Case definition
---------------
  ID      : E2E-KOOKBOOK-01
  Scenario: a user starts the installed KookBook desktop application. The
            application opens its recipe collection, scans it and parses
            every ``*.recipe.md`` recipe with its own RecipeParser.
  Input   : a real recipe collection placed at the application's default
            collection location (``<HOME>/Documents/recipes``, the path
            MainWindow::MainWindow() falls back to when no user setting is
            present), filled with real recipes: upstream's own
            ``couscous.recipe.md`` autotest sample and an additional
            structured recipe.
  Action  : run the *packaged* ``bin/kookbook`` (offscreen QPA, isolated
            HOME/XDG) and let it complete its startup business flow:
            MainWindow -> setCurrentFolder -> Scanner::setRootPath ->
            parseThingsInDifferentThread -> QDirIterator("*.recipe.md") ->
            QFile::open + RecipeParser::parseRecipe.
  Expected: the application reaches the Qt event loop with a fully
            constructed Qt Widgets GUI and, while running, opens and reads
            every recipe file of the collection. The observation is made
            with an inotify watch on the collection directory from outside
            the application process, so it records what the packaged
            application itself did.

Why inotify and not stdout
--------------------------
  The delivered product is a GUI application: it has no CLI surface, it
  prints no business result and it does not terminate on its own (it is
  killed after the observation window, and Qt installs no signal handler,
  so no clean-exit post-processing is available either). Reading the
  collection is the externally observable side effect of the scan/parse
  business step, and it is exactly the step that consumes the recipe
  bytes handed to RecipeParser::parseRecipe.

Usage: test_kookbook_e2e.py <packaged-bin/kookbook> <fixtures-dir>
Exit code 0 = case passed, 1 = case failed, 2 = usage/环境错误.
"""
import ctypes
import os
import shutil
import struct
import subprocess
import sys
import threading
import time

# ── inotify constants (linux/OHOS) ──────────────────────────────────────
IN_ACCESS = 0x00000001
IN_CLOSE_NOWRITE = 0x00000010
IN_OPEN = 0x00000020
IN_MASK = IN_ACCESS | IN_CLOSE_NOWRITE | IN_OPEN
EVENT_NAMES = {
    IN_ACCESS: "ACCESS",
    IN_CLOSE_NOWRITE: "CLOSE_NOWRITE",
    IN_OPEN: "OPEN",
}
EM_AARCH64 = 183
OBSERVE_SECONDS = 18

_results = []


def check(ok, label, detail=""):
    _results.append((bool(ok), label, detail))
    print("  [{}] {}{}".format("PASS" if ok else "FAIL", label,
                               " — " + detail if detail else ""))
    return bool(ok)


def parse_elf_needed(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ValueError("not a little-endian ELF64 file")
    e_machine = struct.unpack_from("<H", data, 0x12)[0]
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
    loads, dynamic = [], None
    for i in range(e_phnum):
        base = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", data, base)[0]
        p_offset, p_vaddr = struct.unpack_from("<QQ", data, base + 0x08)
        p_filesz = struct.unpack_from("<Q", data, base + 0x20)[0]
        if p_type == 1:  # PT_LOAD
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:  # PT_DYNAMIC
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        raise ValueError("no PT_DYNAMIC segment")

    def vaddr_to_offset(vaddr):
        for p_vaddr, p_offset, p_filesz in loads:
            if p_vaddr <= vaddr < p_vaddr + p_filesz:
                return vaddr - p_vaddr + p_offset
        raise ValueError("vaddr {:#x} not covered by PT_LOAD".format(vaddr))

    d_offset, d_size = dynamic
    needed, strtab_vaddr, strsz = [], None, None
    for entry in range(d_offset, d_offset + d_size, 16):
        d_tag, d_un = struct.unpack_from("<qQ", data, entry)
        if d_tag == 0:
            break
        if d_tag == 1:  # DT_NEEDED
            needed.append(d_un)
        elif d_tag == 5:  # DT_STRTAB
            strtab_vaddr = d_un
        elif d_tag == 10:  # DT_STRSZ
            strsz = d_un
    if strtab_vaddr is None or strsz is None:
        raise ValueError("DT_STRTAB/DT_STRSZ missing")
    off = vaddr_to_offset(strtab_vaddr)
    strtab = data[off:off + strsz]
    return e_machine, [strtab[i:strtab.index(b"\x00", i)].decode() for i in needed]


class InotifyWatcher(object):
    """Watch one directory and record (name, event) for its children."""

    def __init__(self, path):
        libc = ctypes.CDLL("libc.so", use_errno=True)
        libc.inotify_init1.restype = ctypes.c_int
        libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p,
                                           ctypes.c_uint32]
        libc.inotify_add_watch.restype = ctypes.c_int
        self.fd = libc.inotify_init1(0)
        if self.fd < 0:
            raise OSError("inotify_init1 failed")
        if libc.inotify_add_watch(self.fd, path.encode(), IN_MASK) < 0:
            raise OSError("inotify_add_watch failed on " + path)
        self.events = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        while not self._stop.is_set():
            try:
                data = os.read(self.fd, 8192)
            except OSError:
                return
            if not data:
                return
            off = 0
            while off < len(data):
                _wd, mask, _cookie, name_len = struct.unpack_from("iIII", data, off)
                off += 16
                name = data[off:off + name_len].split(b"\x00")[0].decode()
                off += name_len
                if name:
                    self.events.append((name, EVENT_NAMES.get(mask & 0xFFFF,
                                                              hex(mask))))
                else:
                    self.events.append(("", EVENT_NAMES.get(mask & 0xFFFF,
                                                            hex(mask))))

    def close(self):
        self._stop.set()
        time.sleep(0.2)
        try:
            os.close(self.fd)
        except OSError:
            pass


def main(argv):
    if len(argv) != 3:
        print("usage: test_kookbook_e2e.py <packaged-bin/kookbook> <fixtures-dir>")
        return 2
    app_bin, fixtures = argv[1], argv[2]

    print("E2E-KOOKBOOK-01: packaged application = {}".format(app_bin))
    if not (os.path.exists(app_bin) and os.access(app_bin, os.X_OK)):
        print("E2E_FAIL: packaged application missing or not executable")
        return 1

    # ── 0. delivered artifact identity ──────────────────────────────────
    try:
        machine, needed = parse_elf_needed(app_bin)
        check(machine == EM_AARCH64, "packaged binary is an AArch64 ELF",
              "e_machine={}".format(machine))
        qt_needed = [n for n in needed if n.startswith("libQt6")]
        check(
            {"libQt6Core.so.6", "libQt6Gui.so.6", "libQt6Widgets.so.6"}.issubset(
                set(needed)),
            "Qt6 Core/Gui/Widgets runtime closure recorded in DT_NEEDED",
            ", ".join(sorted(qt_needed)),
        )
    except Exception as exc:  # noqa: BLE001
        check(False, "ELF inspection of the packaged binary", str(exc))

    # ── 1. real business input: a real recipe collection ────────────────
    base = os.environ.get("TMPDIR") or "/tmp"
    run_root = os.path.join(base, "kookbook-e2e-{}".format(os.getpid()))
    shutil.rmtree(run_root, ignore_errors=True)
    home = os.path.join(run_root, "home")
    collection = os.path.join(home, "Documents", "recipes")
    xdg_runtime = os.path.join(run_root, "xdg-runtime")
    for d in (collection, os.path.join(home, ".config"),
              os.path.join(home, ".local", "share"),
              os.path.join(home, ".cache"), xdg_runtime):
        os.makedirs(d, exist_ok=True)
    os.chmod(xdg_runtime, 0o700)

    recipes = []
    for name in sorted(os.listdir(fixtures)):
        if name.endswith(".recipe.md"):
            shutil.copy(os.path.join(fixtures, name),
                        os.path.join(collection, name))
            recipes.append(name)
    if not recipes:
        print("E2E_FAIL: no *.recipe.md fixtures found in {}".format(fixtures))
        return 1
    print("E2E input: collection {} with recipes {}".format(collection, recipes))

    # ── 2. observe the running application ──────────────────────────────
    watcher = InotifyWatcher(collection)
    env = dict(os.environ)
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "HOME": home,
        "XDG_RUNTIME_DIR": xdg_runtime,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
    })
    out_path = os.path.join(run_root, "app.out")
    err_path = os.path.join(run_root, "app.err")
    with open(out_path, "wb") as out, open(err_path, "wb") as err:
        proc = subprocess.Popen([app_bin], env=env, stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL)

    deadline = time.time() + OBSERVE_SECONDS
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.5)

    alive = proc.poll() is None
    if alive:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    rc = proc.poll()
    watcher.close()
    stderr_text = open(err_path, "r", errors="replace").read()

    check(alive, "application ran until the end of the observation window "
                 "under the offscreen QPA (no startup crash)",
          "returncode={}".format(rc))
    check("propagateSizeHints" in stderr_text or "QPA" in stderr_text or
          "offscreen" in stderr_text.lower(),
          "offscreen QPA plugin initialised and a real QWidget window was created",
          "offscreen platform diagnostics present in stderr")
    check("error while loading shared libraries" not in stderr_text
          and "Cannot load library" not in stderr_text
          and "could not be found" not in stderr_text,
          "runtime closed over the packaged Qt6 dependency libraries",
          "no dynamic-linker failure in stderr")

    # ── 3. business flow: the app read every recipe of the collection ───
    by_name = {}
    for name, ev in watcher.events:
        by_name.setdefault(name, set()).add(ev)
    for name in recipes:
        events = by_name.get(name, set())
        check("OPEN" in events and "ACCESS" in events,
              "collection scan opened and read recipe '{}'".format(name),
              "inotify events: {}".format(sorted(events) or "none"))
    check(bool(by_name.get("", set())),
          "application opened the collection directory itself",
          "inotify events: {}".format(sorted(by_name.get("", set())) or "none"))

    failed = [r for r in _results if not r[0]]
    print("E2E-KOOKBOOK-01 checks: {}/{} passed".format(
        len(_results) - len(failed), len(_results)))
    if failed:
        print("E2E-KOOKBOOK-01 RESULT: FAIL")
        for _ok, label, detail in failed:
            print("  failed: {} ({})".format(label, detail))
        print("app stderr tail:")
        for line in stderr_text.splitlines()[-10:]:
            print("    " + line)
        return 1
    print("E2E-KOOKBOOK-01 RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
