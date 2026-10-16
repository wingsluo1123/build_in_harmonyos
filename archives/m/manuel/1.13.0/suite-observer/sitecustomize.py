"""Observe the original unittest entry without modifying tests or expectations."""
import atexit
import doctest
import json
import os
from collections import defaultdict

report_path = os.environ.get('MANUEL_SUITE_REPORT')
if report_path:
    original_run = doctest.DocTestRunner.run
    depth = 0
    counts = defaultdict(lambda: {'attempted': 0, 'failed': 0, 'calls': 0})
    nested = {'attempted': 0, 'failed': 0, 'calls': 0}

    def observed_run(self, test, *args, **kwargs):
        global depth
        outer = depth == 0
        depth += 1
        try:
            result = original_run(self, test, *args, **kwargs)
        finally:
            depth -= 1
        row = counts[os.path.basename(test.filename or test.name)] if outer else nested
        row['attempted'] += result.attempted
        row['failed'] += result.failed
        row['calls'] += 1
        return result

    doctest.DocTestRunner.run = observed_run

    @atexit.register
    def save_counts():
        corpus_names = {'index.txt', 'table-example.txt', 'README.txt', 'bugs.txt', 'capture.txt', 'tests.py'}
        corpus_rows = [row for name, row in counts.items() if name in corpus_names]
        report = {
            'unit': 'executed original corpus doctest examples',
            'per_file': dict(counts),
            'attempted': sum(x['attempted'] for x in corpus_rows),
            'failed': sum(x['failed'] for x in corpus_rows),
            'outermost_auxiliary': {name: row for name, row in counts.items() if name not in corpus_names},
            'nested_demonstrations_separate': nested,
            'note': 'MyST uses code blocks. Auxiliary memory doctests and nested intentional failure demonstrations are separate from the original corpus denominator.',
        }
        with open(report_path, 'w', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
