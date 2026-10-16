#!/usr/bin/env python3
"""Strict original Groonga command-fixture runner; target use is delegated to root."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from upstream_fixture_parser import commands, expected_responses, actual_responses, json_semantically_equal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--groonga', required=True)
    parser.add_argument('--fixtures', type=Path, required=True, help='Original test/command/suite directory')
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
    cases = inventory['cases']
    if len(cases) != inventory['selected_count'] or len({case['path'] for case in cases}) != len(cases):
        raise ValueError('Invalid or duplicate selected inventory')
    # Validate the entire immutable selection before starting any command.
    prepared = []
    for case in cases:
        relative = Path(case['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe fixture path')
        test = args.fixtures / relative
        oracle = test.with_suffix('.expected')
        test_bytes, oracle_bytes = test.read_bytes(), oracle.read_bytes()
        if hashlib.sha256(test_bytes).hexdigest() != case['test_sha256'] or hashlib.sha256(oracle_bytes).hexdigest() != case['oracle_sha256']:
            raise ValueError('Original fixture/oracle hash mismatch: ' + case['path'])
        source = test_bytes.decode('utf-8')
        expected = expected_responses(source, oracle_bytes.decode('utf-8'))
        if len(expected) != case['logical_commands']:
            raise ValueError('Declared response count mismatch')
        prepared.append((case, '\n'.join(commands(source)) + '\n', expected))
    args.output.mkdir(parents=True, exist_ok=True)
    os.chmod(args.output, 0o770)
    results = []
    for number, (case, stdin, expected) in enumerate(prepared):
        run_dir = Path(tempfile.mkdtemp(prefix=f'{number:02d}-', dir=args.output)).resolve()
        os.chmod(run_dir, 0o770)
        command = [args.groonga, '-n', str(run_dir / 'db')]
        stdout, stderr, exit_code = '', '', None
        executed = False
        try:
            process = subprocess.run(command, input=stdin, capture_output=True, text=True,
                                     encoding='utf-8', cwd=run_dir, timeout=120)
            executed = True
            stdout, stderr, exit_code = process.stdout, process.stderr, process.returncode
            actual = actual_responses(stdout)
            matches = json_semantically_equal(actual, expected)
            errors = [] if matches else ['original JSON oracle mismatch']
            if len(actual) != len(expected):
                errors.append(f'response count {len(actual)} != {len(expected)}')
            if exit_code != 0:
                errors.append(f'runner exit={exit_code}')
            passed = exit_code == 0 and matches
        except Exception as error:
            errors, passed = [str(error)], False
            actual = None
            if isinstance(error, subprocess.TimeoutExpired):
                executed = True
                stdout = (error.stdout or b'').decode('utf-8',errors='replace') if isinstance(error.stdout, bytes) else error.stdout or ''
                stderr = (error.stderr or b'').decode('utf-8',errors='replace') if isinstance(error.stderr, bytes) else error.stderr or ''
        (run_dir/'stdout.log').write_text(stdout,encoding='utf-8')
        (run_dir/'stderr.log').write_text(stderr,encoding='utf-8')
        (run_dir/'expected-normalized.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if actual is not None:
            (run_dir/'actual-normalized.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        result = {'name':case['path'],'executed':executed,'passed':passed,'exit_code':exit_code,
                  'logical_commands':case['logical_commands'],'errors':errors,'log_dir':str(run_dir)}
        results.append(result)
        print(('ok' if passed else 'not ok') + f' {number+1} - ' + case['path'], flush=True)
    report = {'source_discovered':inventory['source_count'],'selected':len(cases),
              'executed':sum(case['executed'] for case in results),'passed':sum(case['passed'] for case in results),
              'failed':sum(not case['passed'] for case in results),'unselected':inventory['source_count']-len(cases),
              'normalization':'Only outer JSON response header indices1(timestamp) and2(duration) normalized to0.0; all result fields checked',
              'status':'passed' if all(case['passed'] for case in results) else 'failed','cases':results}
    (args.output/'selected-upstream-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('GROONGA_SELECTED_UPSTREAM_RESULT='+json.dumps(report,ensure_ascii=False),flush=True)
    return 0 if report['failed']==0 and report['executed']==len(cases) else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('GROONGA_SELECTED_UPSTREAM_SETUP_ERROR='+str(error),file=sys.stderr)
        sys.exit(1)
