import os
import shutil
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument("package_folder", type=Path)
    parser.add_argument("--run-upstream-local", action="store_true")
    parser.add_argument("--rdiff-backup-package", type=Path)
    return parser.parse_args()


def _prepend_env_path(env, name, path):
    old_value = env.get(name)
    env[name] = str(path) if not old_value else str(path) + os.pathsep + old_value


def _make_executable(path):
    path.chmod(path.stat().st_mode | 0o755)


def _site_packages(root):
    candidates = list(root.glob("lib/python*/site-packages"))
    candidates += list(root.glob("lib/python/site-packages"))
    for candidate in candidates:
        if (candidate / "rdiff_backup").is_dir():
            return candidate
    raise SystemExit(f"rdiff_backup site-packages directory was not found under {root}")


def _prepare_rdiff_backup_runtime(package_root, workdir, env):
    if not package_root:
        return
    if not package_root.is_dir():
        raise SystemExit(f"rdiff-backup package directory is missing: {package_root}")

    runtime_root = workdir / "rdiff-backup-runtime"
    shutil.copytree(package_root, runtime_root, symlinks=True)

    bin_dir = runtime_root / "bin"
    rdiff_backup = bin_dir / "rdiff-backup"
    if not rdiff_backup.is_file():
        raise SystemExit(f"rdiff-backup command is missing: {rdiff_backup}")

    for path in bin_dir.glob("*"):
        if path.is_file():
            _make_executable(path)
    extension_patterns = [
        "lib/python*/site-packages/**/*.so",
        "lib/python/site-packages/**/*.so",
    ]
    for pattern in extension_patterns:
        for path in runtime_root.glob(pattern):
            if path.is_file():
                _make_executable(path)

    _prepend_env_path(env, "PATH", bin_dir)
    _prepend_env_path(env, "PYTHONPATH", _site_packages(runtime_root))
    lib_dir = runtime_root / "lib"
    if lib_dir.is_dir():
        _prepend_env_path(env, "LD_LIBRARY_PATH", lib_dir)
    env["SAFEKEEP_TEST_RDIFF_BACKUP"] = str(rdiff_backup)


def _require_executable(exe, env):
    if not shutil.which(exe, path=env.get("PATH")):
        raise SystemExit(f"missing test executable: {exe}")


args = _parse_args()
package_folder = args.package_folder
script = package_folder / "bin" / "safekeep"
share = package_folder / "share" / "safekeep"
upstream_test = share / "safekeep-test"
config = share / "safekeep.conf"
doc = share / "doc" / "safekeep.txt"
sample = share / "samples" / "sample.backup"

for path in (script, upstream_test, config, doc, sample):
    if not path.is_file():
        raise SystemExit(f"missing packaged file: {path}")

if not os.access(script, os.X_OK):
    raise SystemExit(f"safekeep is not executable: {script}")

text = script.read_text(encoding="utf-8")
expected_markers = [
    "#!/usr/bin/env python3",
    'VERSION = "1.5.1"',
    "def usage(exitcode=None):",
    "rdiff-backup",
    "if __name__ == '__main__':",
]
for marker in expected_markers:
    if marker not in text:
        raise SystemExit(f"missing safekeep script marker: {marker}")

test_text = upstream_test.read_text(encoding="utf-8")
for marker in [
    "def localTest(tmproot):",
    "def remoteTest(tmproot, client, server):",
    "-r now",
    "safekeep --server",
    "SAFEKEEP_TEST_OHOS_LOCAL",
    "SAFEKEEP_TEST_CLIENT",
    "SAFEKEEP_TEST_SERVER",
    "--reps=N",
]:
    if marker not in test_text:
        raise SystemExit(f"missing upstream safekeep-test marker: {marker}")

print("safekeep command, support files, and upstream safekeep-test are packaged")

if args.run_upstream_local:
    tmp_base = Path(os.environ.get("TMPDIR") or Path.cwd() / "tmp")
    tmp_base.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="safekeep-upstream-", dir=str(tmp_base)))
    env = os.environ.copy()
    _prepare_rdiff_backup_runtime(args.rdiff_backup_package, workdir, env)
    for exe in ("safekeep", "rdiff-backup", "find", "xargs", "md5sum", "diff"):
        _require_executable(exe, env)

    env["SAFEKEEP_TEST_OHOS_LOCAL"] = "1"
    env["TMPDIR"] = str(workdir / "tmp")
    env["TEMP"] = env["TMPDIR"]
    env["TMP"] = env["TMPDIR"]
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, str(upstream_test), "--local", "--reps=1"],
        cwd=str(workdir),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout, end="")
    if result.returncode:
        raise SystemExit(f"safekeep upstream local test failed with exit code {result.returncode}")

    print("safekeep upstream local test: 1/1 passed")
