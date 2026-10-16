"""Verify every original testpath program and actual native pytest outcome."""
import hashlib
import json
import sys
from pathlib import Path


def main():
    root = Path(sys.argv[1]).resolve()
    evidence = Path(sys.argv[2]).resolve()
    lock = json.loads((root / 'original-source-tests.json').read_bytes())
    for relative, expected in lock['original_files'].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == lock.get('adapted_files', {}).get(relative, expected), relative
    assert hashlib.sha256((root / 'pyproject.toml').read_bytes()).hexdigest() == lock['adapted_pyproject_sha256']
    expected = lock['original_case_ids']
    assert len(expected) == len(set(expected)) == 14
    sys.path.insert(0, str(root))
    import pytest

    class Records:
        def __init__(self):
            self.collected = []
            self.reports = []
            self.collection_errors = []

        def pytest_collection_modifyitems(self, session, config, items):
            self.collected = [x.nodeid for x in items]
            assert sorted(self.collected) == sorted(expected), 'ORIGINAL_COLLECTION_ID_DRIFT'

        def pytest_collectreport(self, report):
            if report.failed:
                self.collection_errors.append(str(report.longrepr))

        def pytest_runtest_logreport(self, report):
            self.reports.append({'nodeid': report.nodeid, 'phase': report.when, 'outcome': report.outcome})

    plugin = Records()
    rc = int(pytest.main([
        '-q', '-p', 'no:cacheprovider', '--basetemp=' + str(root.parent / 'p'),
        '--junitxml=' + str(evidence / 'original.xml'), 'tests',
    ], plugins=[plugin]))
    calls = [x for x in plugin.reports if x['phase'] == 'call']
    passed = [x['nodeid'] for x in calls if x['outcome'] == 'passed']
    bad = [x for x in plugin.reports if x['outcome'] != 'passed']
    ok = (rc == 0 and sorted(plugin.collected) == sorted(expected)
          and sorted(passed) == sorted(expected) and not bad and not plugin.collection_errors)
    result = {
        'status': 'PASS' if ok else 'FAIL', 'exit_code': rc,
        'registered_programs': 3, 'registered_original_cases': 14,
        'source_archive_sha256': lock['source_archive_sha256'],
        'original_source_sha256': lock['original_files'],
        'tested_source_sha256': {**lock['original_files'], **lock['adapted_files']},
        'adapted_files': lock['adapted_files'],
        'collected_ids': plugin.collected, 'passed_ids': passed,
        'phase_reports': plugin.reports, 'failed_or_skipped': bad,
        'collection_errors': plugin.collection_errors,
    }
    (evidence / 'result.json').write_text(json.dumps(result, sort_keys=True), encoding='utf8')
    print('UPSTREAM_ORIGINAL_PROGRAMS=3/3; UPSTREAM_ORIGINAL_CASES='
          + str(len(passed)) + '/14; SKIP='
          + str(sum(x['outcome'] == 'skipped' for x in plugin.reports)))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
