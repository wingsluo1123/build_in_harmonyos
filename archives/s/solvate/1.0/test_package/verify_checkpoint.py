"""Run unchanged Debian test commands plus real checkpoint CLI regressions.

Python orchestrates private CWDs instead of Debian's installed-doc copy/gunzip.
No upstream test target exists. This is not the original Debian shell script.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--binary', required=True)
parser.add_argument('--data', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--environment', required=True)
args = parser.parse_args()
binary = Path(args.binary).resolve()
data = Path(args.data).resolve()
out = Path(args.output).resolve()
out.mkdir(parents=True, exist_ok=False)
cases = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(name, molecule='bpti'):
    cwd = out/name
    cwd.mkdir()
    for suffix in ['.pdb', '.psf']:
        shutil.copyfile(data/(molecule+suffix), cwd/(molecule+suffix))
    return cwd

def run(name, cwd, argv, checks, limit=600, category='checkpoint-regression'):
    command = [str(binary)]+argv
    rec = {'name': name, 'category': category, 'command': command, 'cwd': str(cwd),
           'started_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'timeout_seconds': limit}
    tick = time.monotonic()
    with (cwd/'stdout.log').open('wb') as stdout, (cwd/'stderr.log').open('wb') as stderr:
        proc = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr)
        try:
            rc = proc.wait(timeout=limit)
            rec['timed_out'] = False
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait()
            rec['timed_out'] = True
    rec.update(returncode=rc, elapsed_seconds=time.monotonic()-tick, finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
    log = (cwd/'stderr.log').read_bytes()
    rec['assertions'] = checks(rc, log)
    rec['passed'] = not rec['timed_out'] and all(rec['assertions'].values())
    rec['outputs'] = [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(cwd.iterdir()) if p.is_file()]
    cases.append(rec)
    (out/'result.json').write_text(json.dumps({'environment': args.environment, 'binary': str(binary), 'binary_sha256': sha(binary),
      'upstream_native_test_target': None, 'distribution_original_commands': 2, 'cases': cases}, indent=2)+'\n', encoding='utf-8')
    print(name, 'PASS' if rec['passed'] else 'FAIL', round(rec['elapsed_seconds'], 3), flush=True)
    assert rec['passed'], name

def success(cwd, prefix):
    def check(rc, log):
        pdb = cwd/(prefix+'.pdb')
        content = pdb.read_bytes() if pdb.exists() else b''
        return {'exit_zero': rc==0, 'completion_marker': b'Solvate ready. No errors.' in log,
                'pdb_contains_atoms': b'ATOM' in content, 'pdb_contains_water': b'TIP3' in content,
                'pdb_contains_no_nan': b'nan' not in content.lower()}
    return check

# Exact original two Debian command argument lists and original upstream inputs.
one = prepare('distribution-1')
run('distribution-1', one, ['-r','20.91','-s','-v','bpti','test1'], success(one,'test1'), category='distribution-original')
two = prepare('distribution-2', 'globh')
run('distribution-2', two, ['-n','2','-r','40.33','-t','2','-bulk','-psf','-ion','globh','test2'], success(two,'test2'), category='distribution-original')

for option, filename in [('-ug','gaussians.lis'), ('-ub','boundary.lis')]:
    checkpoint = (one/filename).read_bytes()
    assert checkpoint.endswith(b'\n')
    # Final value at EOF is legal: only required structural/numeric reads fail.
    normal = prepare('resume-'+option[1:])
    (normal/filename).write_bytes(checkpoint.rstrip(b'\r\n'))
    run(normal.name, normal, ['-r','20.91',option,'bpti','result'], success(normal,'result'))

    next_header = checkpoint.index(b'[', 1)
    last_token = checkpoint.rstrip().rsplit(None, 1)[0]
    variants = [('empty',b''), ('truncated-header', checkpoint.splitlines()[0][:8]),
                ('later-header',checkpoint[:next_header+8]), ('missing-final-number',last_token)]
    for suffix, malformed in variants:
        case = prepare(option[1:]+'-'+suffix)
        (case/filename).write_bytes(malformed)
        def negative(rc, log):
            reached = b'Reading parameter for gaussians' in log if option=='-ug' else b'Reading boundary parameters' in log
            return {'exit_nonzero': rc!=0, 'correct_reader_reached': reached,
                    'fatal_error': b'Solvate terminated with fatal error.' in log,
                    'no_completion_marker': b'Solvate ready. No errors.' not in log,
                    'no_output_pdb': not (case/'result.pdb').exists()}
        run(case.name, case, [option,'bpti','result'], negative, limit=5)

print('SUMMARY distribution=2/2 checkpoint=10/10; host/target identity is the supplied environment label.', flush=True)
