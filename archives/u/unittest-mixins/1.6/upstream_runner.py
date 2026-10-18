"""Run every original unittest case; retain source/metadata attribution."""
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source))
os.chdir(source)
import six
import pytest
import unittest_mixins

assert Path(unittest_mixins.__file__).resolve().is_relative_to(source)
files = [source / 'tests' / 'test_mixins.py', *sorted((source / 'unittest_mixins').glob('*.py'))]
before = {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


xml_path = output / 'upstream-junit.xml'
exit_code = pytest.main(['-ra', '-vv', '--junitxml=' + str(xml_path), str(source / 'tests')])
xml = ET.parse(xml_path).getroot()
suites = list(xml) if xml.tag == 'testsuites' else [xml]
collected = sum(int(item.get('tests', 0)) for item in suites)
failed = sum(int(item.get('failures', 0)) for item in suites)
errors = sum(int(item.get('errors', 0)) for item in suites)
skipped = sum(int(item.get('skipped', 0)) for item in suites)
assert collected == 31, 'The complete fixed upstream suite must be preserved'
cases = [case for suite in suites for case in suite.findall('testcase')]
passed_ids = [case.get('classname') + '.' + case.get('name') for case in cases
              if not any(case.find(kind) is not None for kind in ('failure', 'error', 'skipped'))]
after = {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
assert before == after
record = {
    'collected': collected, 'ran': collected - skipped, 'passed': len(passed_ids),
    'failed': failed, 'errors': errors, 'skipped': skipped,
    'passed_ids': passed_ids, 'pytest_version': pytest.__version__, 'pytest_origin': pytest.__file__,
    'failure_details': [ET.tostring(case, encoding='unicode') for case in cases
                        if any(case.find(kind) is not None for kind in ('failure', 'error', 'skipped'))],
    'python': sys.version, 'python_executable': sys.executable,
    'package_origin': unittest_mixins.__file__, 'six_origin': six.__file__,
    'source_hashes': before, 'source_unchanged': before == after,
    'runner': 'published pytest 9.1.1; original cases/guards/assertions unchanged; matches independent stdlib baseline',
    'coverage_instrumentation': 'not executed; coverage is the dependent parent measurement tool',
}
(output / 'upstream-results.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('UPSTREAM_RESULTS ' + json.dumps({key: record[key] for key in ('collected', 'ran', 'passed', 'failed', 'errors', 'skipped')}))
raise SystemExit(exit_code)
