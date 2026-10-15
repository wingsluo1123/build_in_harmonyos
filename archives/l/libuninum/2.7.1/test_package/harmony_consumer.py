"""One installed OHOS CLI consumer flow, not additional upstream test cases.

Exercise actual file I/O and multi-process UTF-8 conversion on the target:
Western -> Arabic_Western -> Devanagari -> Western_Lower. The longer record
exceeds numconv's initial 32-element input buffer. Each output is consumed by
the next process; compare complete UTF-8 bytes, including final newlines.
This is OHOS runtime coverage, not a claim that the workflow is OS-exclusive.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def verify(path, expected):
    actual = path.read_bytes()
    if actual != expected:
        raise RuntimeError('consumer output mismatch: ' + path.name)


def run(cli, build_folder):
    cli = Path(cli).resolve(strict=True)
    build_folder = Path(build_folder).resolve(strict=True)
    if not cli.is_file() or not os.access(cli, os.X_OK):
        raise RuntimeError('installed numconv is not executable')
    records = ['77', '1234', '6453', '1234567890', '9' * 100]
    original = ('\n'.join(records) + '\n').encode('utf-8')
    systems = [('Arabic_Western', '٠١٢٣٤٥٦٧٨٩'),
               ('Devanagari', '०१२३४५६७८९'),
               ('Western_Lower', '0123456789')]
    # A task-private writable directory, never /tmp or a shared installation.
    with tempfile.TemporaryDirectory(prefix='harmony-numconv-', dir=build_folder) as tmp:
        source = Path(tmp, '鸿蒙数字-输入.txt')
        source.write_bytes(original)
        previous_system = 'Western'
        for index, (system, digits) in enumerate(systems, 1):
            destination = Path(tmp, '数字转换-' + str(index) + '.txt')
            completed = subprocess.run([str(cli), '-f', previous_system, '-t', system,
                '-i', str(source), '-o', str(destination)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
            if completed.stdout or completed.stderr:
                raise RuntimeError('numconv emitted unexpected diagnostics: ' +
                                   repr((completed.stdout, completed.stderr)))
            expected = original.decode('utf-8').translate(
                str.maketrans('0123456789', digits)).encode('utf-8')
            verify(destination, expected)
            source = destination
            previous_system = system
        verify(source, original)
    print('HARMONY_CONSUMER_PASS installed CLI UTF8 file roundtrip (5 records, 3 processes)',
          flush=True)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
