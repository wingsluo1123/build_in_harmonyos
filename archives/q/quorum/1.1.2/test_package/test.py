import gzip
import pathlib
import subprocess
import sys
import tempfile

package = pathlib.Path(sys.argv[1])
perl = pathlib.Path(sys.argv[2])
assert perl.is_file(), 'published Perl executable missing'
bindir = package / 'bin'


def run(name, args=(), input=None):
    command = [str(bindir / name), *map(str, args)]
    if name == 'quorum':
        command.insert(0, str(perl))
    result = subprocess.run(command, input=input, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=90)
    if result.returncode:
        raise RuntimeError((command, result.returncode, result.stdout, result.stderr))
    return result.stdout


def passed(label):
    print('CONSUMER_PASS ' + label, flush=True)


for name in ('quorum', 'quorum_create_database', 'quorum_error_correct_reads', 'merge_mate_pairs', 'split_mate_pairs'):
    assert '1.1.2' in run(name, ['--version'])
passed('installed versions')
with tempfile.TemporaryDirectory(prefix='quorum-consumer-', dir='.') as directory:
    root = pathlib.Path(directory).resolve()
    sequence = 'ACGTGCTAGCTAGGCTACGATGCTAGCTAGCTACGATGCTA'
    text = ''.join('@read%d\n%s\n+\n%s\n' % (i, sequence, 'I' * len(sequence)) for i in range(8))
    fq = root / 'reads.fastq'
    fq.write_text(text)
    merged = run('merge_mate_pairs', [fq, fq])
    assert merged.count('@read') == 16 and merged.count(sequence) == 16
    passed('merge paired reads')
    prefix = root / 'split'
    run('split_mate_pairs', [prefix], '>mate1\nACGT\n>mate2\nTGCA\n')
    assert pathlib.Path(str(prefix) + '_1.fa').read_text() == '>mate1\nACGT\n'
    assert pathlib.Path(str(prefix) + '_2.fa').read_text() == '>mate2\nTGCA\n'
    passed('split paired reads')
    db = root / 'database.jf'
    run('quorum_create_database', ['-s', '10k', '-m', '5', '-t', '1', '-q', '33', '-b', '7', '-o', db, fq])
    assert db.stat().st_size > 100 and b'binary/quorum_db' in db.read_bytes()[:2048]
    passed('create quality database')
    corrected = root / 'corrected'
    run('quorum_error_correct_reads', ['-t', '1', '--min-count', '1', '-o', corrected, db, fq])
    expected = pathlib.Path(str(corrected) + '.fa').read_text()
    assert expected.count('>read') == 8 and sequence in expected
    passed('correct reads')
    compressed = root / 'compressed'
    run('quorum_error_correct_reads', ['-t', '1', '--min-count', '1', '--gzip', '-o', compressed, db, fq])
    with gzip.open(str(compressed) + '.fa.gz', 'rt') as stream:
        assert stream.read() == expected
    passed('gzip output roundtrip')
    front = root / 'frontend'
    run('quorum', ['-s', '10k', '-t', '1', '-k', '5', '-q', '33', '--min-count', '1', '-p', front, fq])
    assert sequence in pathlib.Path(str(front) + '.fa').read_text()
    passed('Perl frontend pipeline')
assert (package / 'share/quorum/adapter.jf').stat().st_size == 62604
passed('installed adapter database')
