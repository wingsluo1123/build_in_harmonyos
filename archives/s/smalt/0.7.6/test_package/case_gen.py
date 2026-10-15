#!/usr/bin/env python3
"""Self-contained deterministic test case for the packaged smalt binary.

The suite must not reach into the recipe's source tree (Conan gives
test_package no reliable handle on it) and must not drag the upstream 69 MB
test/data corpus into the package, so it builds its own tiny reference and read
set instead: a 1200 bp pseudo-random sequence from a fixed-seed LCG (no long
homopolymers, so every read has exactly one best hit) plus five 100 bp reads
taken from known offsets - three exact forward reads, one carrying a single
substitution, and one reverse complement - and a sixth read that cannot map.

Every expected value below was measured from the unmodified upstream 0.7.6
sources (see notes.md): positions are 1-based SAM positions, NM/AS are the
integer tags smalt itself prints.  MAPQ is deliberately *not* asserted to an
exact number: it is derived from candidate-hit counts and is only required to
be a sane integer that agrees between the single- and multi-threaded runs.
"""
import os

REF_LEN = 1200
READ_LEN = 100
REF_NAME = "ref1"

# Index parameters used by every check (upstream defaults are -k 13 -s 2).
KMER = 13
NSKIP = 2

# Fixed RNG seed for the reference, and the seed passed to `smalt map -r`.
REF_SEED = 20260701
MAP_SEED = 42

_OFFSETS = [40, 300, 705]
_MISMATCH_OFFSET = 500
_MISMATCH_INDEX = 50
_REVCOMP_OFFSET = 900

# A read that cannot map anywhere in the reference.
UNMAPPED_NAME = "UNMAPPED_READ"
UNMAPPED_SEQ = "A" * READ_LEN

_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def reference():
    """The deterministic 1200 bp reference sequence."""
    bases = "ACGT"
    state = REF_SEED
    out = []
    run = 0
    prev = None
    while len(out) < REF_LEN:
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        base = bases[(state >> 7) & 3]
        if base == prev:
            run += 1
            if run >= 3:
                base = bases[(state >> 9) & 3]
                if base == prev:
                    base = bases[((state >> 11) & 3) or 1]
                run = 0
        else:
            run = 0
        prev = base
        out.append(base)
    return "".join(out)


def revcomp(seq):
    return seq.translate(_COMPLEMENT)[::-1]


def reads():
    """[(name, sequence, strand, 0-based reference offset)] for the five reads."""
    ref = reference()
    out = []
    for i, off in enumerate(_OFFSETS):
        out.append(("EXACT_FWD_%d" % i, ref[off:off + READ_LEN], "+", off))
    mutated = list(ref[_MISMATCH_OFFSET:_MISMATCH_OFFSET + READ_LEN])
    original = mutated[_MISMATCH_INDEX]
    mutated[_MISMATCH_INDEX] = "A" if original != "A" else "C"
    out.append(("ONE_MISMATCH", "".join(mutated), "+", _MISMATCH_OFFSET))
    out.append(("REVCOMP",
                revcomp(ref[_REVCOMP_OFFSET:_REVCOMP_OFFSET + READ_LEN]),
                "-", _REVCOMP_OFFSET))
    return out


# (qname, SAM flag, 1-based POS, CIGAR, NM:i, AS:i) - measured on unmodified
# upstream smalt 0.7.6 with `index -k 13 -s 2` and `map -f sam -r 42`.
EXPECTED_ALIGNMENTS = [
    ("EXACT_FWD_0", 0, 41, "100M", 0, 100),
    ("EXACT_FWD_1", 0, 301, "100M", 0, 100),
    ("EXACT_FWD_2", 0, 706, "100M", 0, 100),
    ("ONE_MISMATCH", 0, 501, "100M", 1, 97),
    ("REVCOMP", 16, 901, "100M", 0, 100),
]

# `fetchseq <index> ref1 41 20` must return exactly this reference window.
FETCHSEQ_POS = 41
FETCHSEQ_LEN = 20


def fetchseq_expected():
    return reference()[FETCHSEQ_POS - 1:FETCHSEQ_POS - 1 + FETCHSEQ_LEN]


def write_case(workdir):
    """Materialise ref.fa / reads.fq / mixed.fq in workdir; return the paths."""
    os.makedirs(workdir, exist_ok=True)
    ref = reference()
    ref_fa = os.path.join(workdir, "ref.fa")
    with open(ref_fa, "w") as fh:
        fh.write(">%s smalt synthetic reference\n" % REF_NAME)
        for i in range(0, len(ref), 60):
            fh.write(ref[i:i + 60] + "\n")

    reads_fq = os.path.join(workdir, "reads.fq")
    with open(reads_fq, "w") as fh:
        for name, seq, _strand, _off in reads():
            fh.write("@%s\n%s\n+\n%s\n" % (name, seq, "I" * len(seq)))

    mixed_fq = os.path.join(workdir, "mixed.fq")
    with open(reads_fq, encoding="utf-8") as src, open(mixed_fq, "w") as dst:
        dst.write(src.read())
        dst.write("@%s\n%s\n+\n%s\n" % (UNMAPPED_NAME, UNMAPPED_SEQ,
                                        "I" * len(UNMAPPED_SEQ)))
    return {"ref_fa": ref_fa, "reads_fq": reads_fq, "mixed_fq": mixed_fq,
            "read_count": len(reads())}


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = write_case(target)
    print("wrote %(ref_fa)s %(reads_fq)s %(mixed_fq)s" % paths)
    for row in EXPECTED_ALIGNMENTS:
        print("EXPECT %s flag=%d pos=%d cigar=%s NM=%d AS=%d" % row)
