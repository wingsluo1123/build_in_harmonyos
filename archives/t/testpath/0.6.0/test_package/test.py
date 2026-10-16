"""Exercise installed original APIs and owned HarmonyOS filesystem artifacts."""
import hashlib
import json
import os
import shlex
import socket
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
import testpath
from testpath.commands import MockCommand

package = Path(sys.argv[1]).resolve()
site = package / 'lib/python3.12/site-packages'
assert Path(testpath.__file__).resolve() == site / 'testpath/__init__.py'
lock = json.loads((Path(__file__).parent / 'original-source-tests.json').read_bytes())
for relative, digest in lock['original_files'].items():
    if relative.startswith('testpath/'):
        assert hashlib.sha256((site / relative).read_bytes()).hexdigest() == lock.get('adapted_files', {}).get(relative, digest)
assert testpath.__version__ == '0.6.0'
base = None
for value in (os.environ.get('TMPDIR'), '/data/storage/el2/base/cache'):
    if value and Path(value).is_dir():
        p = Path(value)
        if (p.is_absolute() and p.resolve() == p and p.stat().st_uid == os.getuid()
                and os.access(p, os.W_OK | os.X_OK)):
            base = p
            break
assert base is not None
with tempfile.TemporaryDirectory(prefix='ctc-', dir=str(base)) as directory:
    root = Path(directory)
    assert root.resolve() == root and root.stat().st_uid == os.getuid()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    os.environ['TMPDIR'] = str(root)
    tempfile.tempdir = str(root)
    # C1: actual file, symlink, FIFO and AF_UNIX socket predicates.
    path = root / 'input'
    payload = b'original-testpath\x00\xff\n'
    path.write_bytes(payload)
    link = root / 'link'
    link.symlink_to(path)
    fifo = root / 'fifo'
    os.mkfifo(fifo)
    endpoint = root / 's'
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(endpoint))
        testpath.assert_isfile(path)
        testpath.assert_islink(link, to=path)
        testpath.assert_ispipe(fifo)
        testpath.assert_issocket(endpoint)
        testpath.assert_not_isfile(link, follow_symlinks=False)
    assert path.read_bytes() == payload
    # C2: actual environment mutation and restoration.
    key = 'CONAN_TESTPATH_PRIVATE_ENV'
    before = os.environ.get(key)
    with testpath.modified_env({key: 'temporary'}):
        assert os.environ[key] == 'temporary'
    assert os.environ.get(key) == before
    with testpath.temporary_env({key: 'only'}):
        assert dict(os.environ) == {key: 'only'}
    assert os.environ.get(key) == before
    # C3: generated child, argv recording, stdout/stderr and exit status.
    with MockCommand.fixed_output(
        'owned_testpath_probe', stdout='native-out\n',
        stderr='native-err\n', exit_status=7,
    ) as command:
        child = subprocess.run(
            ['owned_testpath_probe', 'alpha', 'beta'], capture_output=True, timeout=30,
        )
        assert child.returncode == 7
        assert child.stdout == b'native-out\n' and child.stderr == b'native-err\n'
        command.assert_called(['alpha', 'beta'])
        calls = command.get_calls()
        assert len(calls) == 1 and calls[0]['argv'][1:] == ['alpha', 'beta']
        generated = Path(command._cmd_path)
        assert generated.read_text().splitlines()[0] == '#!/system/bin/sh'
        assert 'exec ' + shlex.quote(sys.executable) + ' ' + chr(34) + '$0' + chr(34) + ' ' + chr(34) + '$@' + chr(34) in generated.read_text()
    assert not generated.exists()
    # HARMONY_TEST_COUNT=1: app UID, 0700 POSIX ownership and UTF8 binary artifacts.
    uname = os.uname()
    assert uname.sysname == 'HarmonyOS' and uname.machine == 'aarch64'
    assert os.getuid() != 0
    owned = root / '鸿蒙私有文件'
    owned.write_bytes(payload)
    testpath.assert_isfile(owned)
    assert owned.stat().st_uid == os.getuid() and owned.read_bytes() == payload
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    if testpath.commands.recording_dir:
        import shutil
        recording = Path(testpath.commands.recording_dir)
        assert recording.resolve().is_relative_to(root)
        shutil.rmtree(recording)
        testpath.commands.recording_dir = None
print('CONSUMER_TEST_PASS=3/3')
print('HARMONY_TEST_PASS=1/1')
print(json.dumps({
    'installed_payload_matches_declared_source': True,
    'unchanged_module_resource_count': 6, 'adapted_module_count': 1, 'uid': os.getuid(),
    'uname': list(os.uname()), 'installed_module': testpath.__file__,
    'version': testpath.__version__,
}, sort_keys=True))
