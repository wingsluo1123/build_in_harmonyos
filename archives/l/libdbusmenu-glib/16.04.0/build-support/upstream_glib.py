"""Run the eight original GLib test entries from the pinned release.

The original Makefile recipes generate the original scripts; C sources and
assertions are never rewritten. Counts in this file describe entry inventory,
not a claim that those entries passed.
"""
import hashlib
import json
import os
import stat
import tempfile
from xml.sax.saxutils import escape
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

MAKE_SHA256 = "9be15326b3e8b7703b78ed84511695aba3175672e9fe2514343a495041ac34f7"
ENTRIES = (
    "test-glib-objects-test", "test-glib-events", "test-glib-events-nogroup",
    "test-glib-layout", "test-glib-properties", "test-glib-proxy",
    "test-glib-simple-items", "test-glib-submenu",
)

def inventory(source):
    tests = Path(source) / "tests"
    raw = (tests / "Makefile.am").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MAKE_SHA256:
        raise RuntimeError("Original test Makefile differs from pinned release")
    text = raw.decode("utf8")
    joined = re.sub(r"\\\r?\n", " ", text)
    declared = re.search(r"(?m)^TESTS\s*=([^\n]+)", joined).group(1).split()
    if tuple(declared) != ENTRIES:
        raise RuntimeError("Original GLib entry inventory changed")
    programs = re.search(r"(?m)^check_PROGRAMS\s*=([^\n]+)", joined).group(1).split()
    if len(programs) != 15 or len(set(programs)) != 15:
        raise RuntimeError("Original GLib program inventory changed")
    sources = {}
    for name in programs:
        key = name.replace("-", "_") + "_SOURCES"
        matches = re.findall(r"(?m)^" + re.escape(key) + r"\s*=([^\n]+)", joined)
        if len(matches) != 1:
            raise RuntimeError("Unbound original program sources: " + name)
        files = matches[0].split()
        if not files or not any(p.endswith(".c") for p in files):
            raise RuntimeError("Missing original C program: " + name)
        for leaf in files:
            p = tests / leaf
            if not p.is_file() or p.is_symlink() or Path(leaf).name != leaf:
                raise RuntimeError("Unsafe/missing original test source: " + leaf)
        sources[name] = [leaf for leaf in files if leaf.endswith(".c")]
    recipes = []
    lines = text.splitlines(keepends=True)
    for entry in ENTRIES:
        if entry == "test-glib-simple-items":
            continue  # The original TESTS entry is the original executable.
        starts = [i for i, line in enumerate(lines) if line.startswith(entry + ":")]
        if len(starts) != 1:
            raise RuntimeError("Missing original generator recipe: " + entry)
        start = starts[0]
        end = start + 1
        while end < len(lines) and (not lines[end].strip() or lines[end].startswith(("\t", "#"))):
            end += 1
        block = "".join(lines[start:end])
        if "$(DBUS_RUNNER)" not in block or "@chmod +x $@" not in block:
            raise RuntimeError("Incomplete original generator recipe: " + entry)
        recipes.append(block)
    blobs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in tests.iterdir() if p.is_file() and
             (p.name in {leaf for items in sources.values() for leaf in items} or
              p.name.endswith(".h"))}
    return {"entries": list(ENTRIES), "programs": sources, "original_source_sha256": blobs,
            "makefile_sha256": MAKE_SHA256}, recipes

def _private_temp_directory(prefix):
    rejected = []
    candidates = [os.environ.get("TMPDIR"), tempfile.gettempdir(),
                  "/data/storage/el2/base/cache", "/data/service/hnp/tmp",
                  str(Path.home())]
    seen = set()
    for value in candidates:
        if not value or value in seen:
            continue
        seen.add(value)
        manager = None
        try:
            supplied = Path(value)
            if not supplied.is_absolute():
                raise RuntimeError("relative parent")
            base = supplied.resolve(strict=True)
            if (not base.is_dir() or base.stat().st_uid != os.getuid()
                    or any(p.is_symlink() for p in (base, *base.parents))
                    or not os.access(base, os.W_OK | os.X_OK)):
                raise RuntimeError("parent ownership or write access")
            manager = tempfile.TemporaryDirectory(prefix=prefix, dir=str(base))
            private = Path(manager.name)
            metadata = private.lstat()
            if (private.is_symlink() or private.resolve(strict=True) != private
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o700
                    or len(os.fsencode(private / "dbus-XXXXXXXXXXXXXXXX")) >= 108):
                raise RuntimeError("private owner, mode, canonical path or socket length")
            return manager
        except (OSError, RuntimeError) as error:
            if manager is not None:
                manager.cleanup()
            rejected.append(str(value) + ": " + type(error).__name__ + ": " + str(error))
    raise RuntimeError("No suitable UID-owned private POSIX temporary directory; "
                       + "; ".join(rejected))

def _capture_original_process(argv, cwd, environment, timeout):
    import signal
    import time
    session = os.getsid(0)
    uid = os.getuid()
    process = subprocess.Popen(argv, cwd=cwd, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, process_group=0)
    def exists():
        try:
            os.killpg(process.pid, 0)
            return True
        except ProcessLookupError:
            return False
    def exact_members():
        paths = [p for p in Path('/proc').iterdir() if p.name.isdigit()]
        if len(paths) >= 4096:
            raise RuntimeError('Owned process-group inspection bound exceeded')
        members = []
        for p in paths:
            try:
                fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) != process.pid:
                    continue
                if p.stat().st_uid != uid or int(fields[3]) != session:
                    raise RuntimeError('Process-group owner/session mismatch')
                members.append((int(p.name), fields[19]))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
        if exists() and not members:
            raise RuntimeError('Live process group cannot be bound; no signal sent')
        return members
    def stop_owned_group():
        for sig in (signal.SIGTERM, signal.SIGKILL):
            if not exists():
                break
            members = exact_members()
            for pid, start in members:
                try:
                    actual = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
                    if actual != start:
                        raise RuntimeError('Process start identity changed; no signal sent')
                except (FileNotFoundError, ProcessLookupError):
                    pass
            os.killpg(process.pid, sig)
            time.sleep(1)
    try:
        output, error = process.communicate(timeout=timeout)
        for _ in range(20):
            if not exists():
                break
            time.sleep(0.1)
        if exists():
            stop_owned_group()
            raise RuntimeError('Original command returned with an owned process group still alive')
        return process.returncode, output, error
    except subprocess.TimeoutExpired:
        stop_owned_group()
        process.communicate(timeout=5)
        raise

def run(config):
    cfg = json.loads(Path(config).read_text(encoding="utf8"))
    source = Path(cfg["source"])
    report, recipes = inventory(source)
    root = Path(cfg["build"]) / "original-glib-tests"
    root.mkdir(exist_ok=False)
    for tool in ("cc", "make", "runner", "gtester", "daemon", "shell"):
        p = Path(cfg[tool][0] if tool == "cc" else cfg[tool])
        if not p.is_absolute() or not p.is_file():
            raise RuntimeError("Actual target tool is missing: " + tool)
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(dict.fromkeys(
        [str(Path(cfg[k]).parent) for k in ("gtester", "daemon", "runner")] +
        env.get("PATH", "").split(os.pathsep)))
    env["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(
        [str(Path(cfg["package"]) / "lib")] + cfg["runtime_dirs"] +
        env.get("LD_LIBRARY_PATH", "").split(os.pathsep)))
    # The original runner starts its daemon in a cleared environment unless
    # --keep-env is explicitly selected. Bind the actual declared daemon and
    # a task-private config instead of trusting PATH or its build-time prefix.
    with _private_temp_directory("dbmenu-") as name:
        private = Path(name)
        metadata = private.lstat()
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise RuntimeError("Private bus root owner/mode mismatch")
        if len(os.fsencode(private / "dbus-XXXXXXXXXXXXXXXX")) >= 108:
            raise RuntimeError("Private D-Bus socket path exceeds sockaddr_un")
        env["TMPDIR"] = str(private)
        busconfig = root / "private-session.conf"
        uid = str(os.getuid())
        text = ("<busconfig><type>session</type><listen>unix:tmpdir=" +
                escape(str(private)) + "</listen><auth>EXTERNAL</auth>" +
                '<policy context="default"><deny user="*"/><allow user="' + uid +
                '"/></policy><policy user="' + uid +
                '"><allow own="*"/><allow send_destination="*"/>' +
                '<allow receive_sender="*"/></policy></busconfig>')
        fd = os.open(busconfig, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf8") as stream:
            stream.write(text)
        report["actual_runner_daemon"] = cfg["daemon"]
        report["bus_config_sha256"] = hashlib.sha256(busconfig.read_bytes()).hexdigest()
        report["private_bus_root"] = str(private)
        report["private_bus_uid"] = os.getuid()
        records = []
        def call(name, argv):
            rc, output, error = _capture_original_process(argv, root, env, 300)
            for stream, data in (("stdout", output), ("stderr", error)):
                with (root / (name + "." + stream)).open("xb") as destination:
                    destination.write(data)
            row = {"name": name, "argv": argv, "rc": rc,
                   "output_capture": "EOF_FROM_ALL_INHERITED_WRITERS",
                   "owned_command_process_group_empty": True}
            for stream in ("stdout", "stderr"):
                row[stream + "_sha256"] = hashlib.sha256((root / (name + "." + stream)).read_bytes()).hexdigest()
            records.append(row)
            (root / "progress.json").write_text(json.dumps({**report, "records": records,
                "full_pass": False}, indent=2), encoding="utf8")
            if rc:
                # Preserve the exact captured streams in CI as well as frozen files.
                # This changes diagnostics only; argv, timeout, status and oracles stay intact.
                print("ORIGINAL_FAILURE_CONTEXT=" + json.dumps({
                    "entry": name, "rc": rc, "argv": argv,
                    "uid": os.getuid(), "private_bus_root": str(private),
                    "stdout_sha256": row["stdout_sha256"],
                    "stderr_sha256": row["stderr_sha256"]}, sort_keys=True), flush=True)
                for stream, data in (("stdout", output), ("stderr", error)):
                    print("ORIGINAL_FAILURE_" + stream.upper() + "_BEGIN", flush=True)
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                    print("\nORIGINAL_FAILURE_" + stream.upper() + "_END", flush=True)
                xml_path = root / "test-glib-objects.xml"
                if xml_path.is_file():
                    data = xml_path.read_bytes()
                    print("ORIGINAL_OBJECT_XML_SHA256=" + hashlib.sha256(data).hexdigest(), flush=True)
                    print("ORIGINAL_OBJECT_XML_BEGIN", flush=True)
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                    print("\nORIGINAL_OBJECT_XML_END", flush=True)
                raise RuntimeError("Original entry/tool failed: " + name)
        # Published self-signed helper ELFs can be rejected for the CI worker UID.
        # Adapt private copies only; the declared published dependency remains byte-identical.
        private_bin = private / "tool-bin"
        private_lib = private / "tool-lib"
        private_bin.mkdir(mode=0o700)
        private_lib.mkdir(mode=0o700)
        glib_prefix = Path(cfg["gtester"]).parent.parent.resolve(strict=True)
        helper_sources = [(Path(cfg["gtester"]), private_bin / "gtester")]
        helper_sources += [(glib_prefix / "lib" / leaf, private_lib / leaf)
                           for leaf in ("libglib-2.0.so.0", "libintl.so.8")]
        report["private_published_tool_copies"] = []
        env["PATH"] = str(private_bin) + os.pathsep + env["PATH"]
        env["LD_LIBRARY_PATH"] = str(private_lib) + os.pathsep + env["LD_LIBRARY_PATH"]
        env["PWD"] = str(root.absolute())
        for original, target in helper_sources:
            actual = original.resolve(strict=True)
            if not actual.is_relative_to(glib_prefix) or not actual.is_file():
                raise RuntimeError("Published helper escaped the declared GLib provider")
            original_bytes = actual.read_bytes()
            if original_bytes[:4] != b"\x7fELF":
                raise RuntimeError("Published helper is not an actual native ELF")
            with target.open("xb") as stream:
                stream.write(original_bytes)
            target.chmod(0o700)
            call("sign-private-" + target.name,
                 [sys.executable, cfg["sign_helper"], str(target)])
            if actual.read_bytes() != original_bytes:
                raise RuntimeError("Published provider changed during private signing")
            report["private_published_tool_copies"].append({
                "published_path": str(actual), "private_path": str(target),
                "published_sha256": hashlib.sha256(original_bytes).hexdigest(),
                "private_signed_sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        private_gtester = str(private_bin / "gtester")
        call("validate-private-gtester", [private_gtester, "--help"])
        # Resolve only the original generator's tool executable; preserve all original arguments.
        object_recipe_count = sum(recipe.count("--task gtester --task-name test") for recipe in recipes)
        if object_recipe_count != 1:
            raise RuntimeError("Original object generator executable binding changed")
        recipes = [recipe.replace("--task gtester --task-name test",
                   "--task " + shlex.quote(private_gtester) + " --task-name test") for recipe in recipes]
        for name, sources in report["programs"].items():
            argv = cfg["cc"] + ["-Wall", "-Werror", "-DG_DISABLE_DEPRECATED",
                    "-I" + str(source), "-I" + str(source / "tests"),
                    "-I" + str(Path(cfg["package"]) / "include/libdbusmenu-glib-0.4")]
            argv += cfg["cflags"] + [str(source / "tests" / p) for p in sources]
            argv += ["-o", str(root / name), "-L" + str(Path(cfg["package"]) / "lib"),
                     "-ldbusmenu-glib"] + cfg["libs"]
            call("compile-" + name, argv)
            if cfg["target_os"] == "OHOS":
                call("sign-" + name, [sys.executable, cfg["sign_helper"], str(root / name)])
        (root / "Makefile.am").write_bytes((source / "tests/Makefile.am").read_bytes())
        runner = shlex.join([cfg["runner"], "--max-wait=0", "--keep-env",
                             "--dbus-daemon=" + cfg["daemon"],
                             "--dbus-config=" + str(busconfig)])
        if "\n" in runner or "$" in runner or "#" in runner:
            raise RuntimeError("Unsafe make runner path")
        (root / "OriginalTests.mk").write_text("OBJECT_XML_REPORT=test-glib-objects.xml\nDBUS_RUNNER=" + runner + "\n" +
                                               "\n".join(recipes), encoding="utf8")
        call("generate-original-scripts", [cfg["make"], "-j1", "-f", "OriginalTests.mk"] +
             [p for p in ENTRIES if p != "test-glib-simple-items"])
        for entry in ENTRIES:
            argv = [str(root / entry)] if entry == "test-glib-simple-items" else [cfg["shell"], str(root / entry)]
            call(entry, argv)
        import xml.etree.ElementTree as ET
        xml = root / "test-glib-objects.xml"
        tree = ET.parse(xml)
        cases = tree.findall(".//testcase")
        if len(cases) != 9 or len({x.get("path") for x in cases}) != 9:
            raise RuntimeError("Incomplete original object case report")
        for case in cases:
            statuses = case.findall("status")
            if len(statuses) != 1 or statuses[0].get("result") != "success" or statuses[0].get("exit-status") != "0":
                raise RuntimeError("Original object case did not pass")
        result = {**report, "records": records, "scope": "EIGHT_ORIGINAL_GLIB_ENTRIES",
                  "full_pass": True, "executed_original_entries": 8,
                  "compiled_original_programs": 15, "gtk_layer_in_scope": False}
        (root / "result.json").write_text(json.dumps(result, indent=2), encoding="utf8")
        print(json.dumps({"original_entries": 8, "original_programs": 15,
                          "original_entry_pass": True, "result": str(root / "result.json")}))

if __name__ == "__main__":
    if sys.argv[1] == "--inventory":
        print(json.dumps(inventory(sys.argv[2])[0], indent=2))
    else:
        run(sys.argv[1])
