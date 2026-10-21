"""Execute preserved reference scenarios plus explicit CLI semantic checks."""
from pathlib import Path
import json
import re
import subprocess
import sys


def fasta(path):
    rows = {}
    key = None
    for line in Path(path).read_text().splitlines():
        if line.startswith(">"):
            key = line[1:].split()[0]
            rows[key] = ""
        elif key:
            rows[key] += "".join(line.split()).replace(".", "").replace("-", "")
    return rows


def clustal(path):
    rows = {}
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and re.fullmatch(r"[A-Za-z.-]+", fields[1]):
            rows[fields[0]] = rows.get(fields[0], "") + fields[1]
    return rows


def preserve(path, expected):
    rows = clustal(path)
    assert rows and len({len(value) for value in rows.values()}) == 1
    assert {key: value.replace("-", "").replace(".", "")
            for key, value in rows.items()} == expected


def main(binary, data, fixtures, output):
    binary = str(Path(binary).resolve())
    data, fixtures, output = map(Path, (data, fixtures, output))
    output.mkdir(parents=True, exist_ok=True)
    matrix = str(data / "blosum80.mat")
    sample = str(data / "multidom.seq")
    expected = fasta(sample)
    rows = []

    def run(name, args, check=None, success=True):
        result = subprocess.run([binary, *map(str, args)], cwd=output,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=120, text=True)
        (output / (name + ".stdout")).write_text(result.stdout)
        (output / (name + ".stderr")).write_text(result.stderr)
        row = {"name": name, "argv": [binary, *map(str, args)],
               "exit": result.returncode, "passed": False}
        rows.append(row)
        try:
            assert (result.returncode == 0) if success else (result.returncode != 0)
            if check:
                check(result)
            row["passed"] = True
            print("PASS " + name, flush=True)
        finally:
            (output / "result.json").write_text(json.dumps(rows, indent=2))

    def reference(_):
        preserve(output / "multidom.aln", expected)
        assert clustal(output / "multidom.aln") == clustal(fixtures / "multidom.clustal")

    run("readme-reference", ["-read_fasta", sample, "-clustal", "multidom.aln", matrix], reference)
    # Preserve all six commands of Debian's run-unit-test. Their original
    # checks are exit status only; best-without-hb may produce an empty file.
    dm = str(fixtures / "blosum80.mat")
    run("debian-1-fasta", ["-read_fasta", fixtures / "test1.fa", "-clustal", "d1.aln", dm],
        lambda _: preserve(output / "d1.aln", fasta(fixtures / "test1.fa")))
    run("debian-2-clustal-pir", ["-read_msa", "d1.aln", "-pir", "d2.pir", dm],
        lambda _: require(fasta(output / "d2.pir") == fasta(fixtures / "test1.fa")))
    run("debian-3-best", ["-read_fasta", fixtures / "test2.fa", "-pir", "d3.pir", "-best", dm])
    run("debian-4-po", ["-read_fasta", fixtures / "test3.fa", "-po", "d4.po", dm],
        lambda _: require("SOURCECOUNT=5" in (output / "d4.po").read_text()))
    run("debian-5-global", ["-read_fasta", fixtures / "test4.fa", "-do_global", "-clustal", "d5.aln", dm],
        lambda _: preserve(output / "d5.aln", fasta(fixtures / "test4.fa")))
    run("debian-6-progressive", ["-read_fasta", fixtures / "test5.fa", "-do_progressive", "-clustal", "d6.aln", dm],
        lambda _: preserve(output / "d6.aln", fasta(fixtures / "test5.fa")))
    run("global-formats", ["-read_fasta", sample, "-do_global", "-clustal", "global.aln",
                          "-pir", "global.pir", "-po", "global.po", matrix],
        lambda _: (preserve(output / "global.aln", expected),
                   require(fasta(output / "global.pir") == expected),
                   require("SOURCECOUNT=4" in (output / "global.po").read_text())))
    run("po-roundtrip", ["-read_msa", "global.po", "-clustal", "round.aln", matrix],
        lambda _: preserve(output / "round.aln", expected))
    run("pir-roundtrip", ["-read_msa", "global.pir", "-clustal", "pir.aln", matrix],
        lambda _: preserve(output / "pir.aln", expected))
    run("progressive-pairs", ["-read_fasta", sample, "-do_progressive", "-read_pairscores",
                              data / "multidom.pscore", "-clustal", "pairs.aln", matrix],
        lambda _: preserve(output / "pairs.aln", expected))
    small = output / "identical.fa"
    # Upstream generate_lpo_bundles rejects paths shorter than 10 residues.
    small.write_text(">alpha\nACGTACGTACGT\n>beta\nACGTACGTACGT\n")
    run("heaviest-consensus", ["-read_fasta", small, "-hb", "-best", "-pir", "best.pir", matrix],
        lambda _: require(any(key.startswith("CONSENS") and value == "ACGTACGTACGT"
                              for key, value in fasta(output / "best.pir").items())))
    run("truncated-matrix", ["-read_fasta", sample, "-clustal", "trunc.aln", data / "blosum80_trunc.mat"],
        lambda _: preserve(output / "trunc.aln", expected))
    run("missing-input", ["-read_fasta", "absent.fa", "-clustal", "absent.aln", matrix], success=False)
    run("missing-matrix", ["-read_fasta", small, "absent.mat"], success=False)
    run("version", ["--version"], lambda p: require(p.stdout.strip() == "poa 2.0-20060928"))
    run("help", ["--help"], lambda p: require("-read_fasta" in p.stderr and "-do_progressive" in p.stderr))
    print(f"CLI_REGRESSION_PASS {len(rows)}/{len(rows)}", flush=True)


def require(condition):
    assert condition


if __name__ == "__main__":
    main(*sys.argv[1:])
