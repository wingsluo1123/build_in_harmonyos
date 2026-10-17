import hashlib,json,os,re,subprocess
from pathlib import Path
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



def run_original(source, output, perl):
    source = Path(source)
    spec = json.loads((source / 'original-source-tests.json').read_bytes())
    files = spec['files']
    actual = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source / 't').rglob('*.t'))}
    assert actual == files and len(files) == 14
    assert hashlib.sha256((source / 'lib/Readonly.pm').read_bytes()).hexdigest() == spec['module_sha256']
    output.mkdir()
    environment = dict(os.environ, HARNESS_VERBOSE='1')
    argv = [perl, '-e', 'use Test::Harness;runtests(@ARGV);', *sorted(files)]
    rc, stdout, stderr = _capture_original_process(argv, source, environment, 300)
    (output / 'stdout').write_bytes(stdout)
    (output / 'stderr').write_bytes(stderr)
    assert rc == 0 and not stderr
    assert b'All tests successful.' in stdout and b'Files=14, Tests=188,' in stdout and b'Result: PASS' in stdout
    seen = {}; current = None
    for line in stdout.decode('utf8').splitlines():
        header = re.match(r'^(t/\S+\.t)\s+\.+', line)
        if header:
            current = header[1]
            assert current in files and current not in seen
            seen[current] = {'assertions':[], 'skips':[],'plan':None}
            continue
        assert not re.match(r'^\s*Bail out!',line,re.I)
        if current is None:
            continue
        plan = re.fullmatch(r'\s*1\.\.(\d+)\s*',line)
        if plan:
            assert seen[current]['plan'] is None
            seen[current]['plan'] = int(plan[1])
        tap = re.match(r'^\s*(not )?ok\s+(\d+)\b(.*)',line)
        if not tap:
            continue
        assert not tap[1] and not re.search(r'#\s*TODO',tap[3],re.I)
        number = int(tap[2]);seen[current]['assertions'].append(number)
        skip = re.search(r'#\s*skip\s*(.*)',tap[3],re.I)
        if skip:
            expected = spec['accepted_not_applicable'].get(current,{})
            assert number in expected.get('assertions',[]) and skip[1] == expected['raw_reason']
            seen[current]['skips'].append(number)
    assert set(seen) == set(files)
    for path, row in seen.items():
        assert row['plan'] == spec['planned_counts'][path]
        assert row['assertions'] == list(range(1,row['plan']+1))
        assert row['skips'] == spec['accepted_not_applicable'].get(path,{}).get('assertions',[])
    assert sum(len(v['assertions']) for v in seen.values()) == 188
    assert sum(len(v['skips']) for v in seen.values()) == 17
    assert actual == {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source / 't').rglob('*.t'))}
    result = {'status':'APPLICABLE_ORIGINAL_ASSERTIONS_PASS_WITH_EXACT_USER_ACCEPTED_GUARDS','registered_programs':14,'executed_programs':14,'registered_assertions':188,'applicable_assertions':171,'passed_applicable_assertions':171,'not_applicable_assertions':17,'raw_tap_skips':17,'todo':0,'failed_assertions':0,'global_188_assertions_pass':False,'source_test_hashes':actual,'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(stderr).hexdigest(),'owned_process_group_empty':True,'per_file':seen}
    (output / 'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result
