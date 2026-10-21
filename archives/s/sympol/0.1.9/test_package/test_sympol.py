"""One installed-package workflow: UTF-8 V -> H -> V exact geometry roundtrip."""
from fractions import Fraction
from pathlib import Path
import re
import subprocess
import sys


def representation(output, kind):
    match = re.search(r"(?m)^" + re.escape(kind) + r"-representation[ \t]*\r?\n"
                      r"(?:[ \t]*\*[^\n]*\n)*begin\s*\n(\d+)\s+(\d+)\s+rational\s*\n"
                      r"(.*?)^end\s*$", output, re.S | re.M)
    if not match:
        raise RuntimeError("missing complete " + kind + " representation")
    count, dimension = map(int, match.group(1, 2))
    rows = [tuple(Fraction(v) for v in line.split())
            for line in match.group(3).splitlines() if line.strip()]
    if (count, dimension) != (4, 3) or len(rows) != count:
        raise RuntimeError("square representation cardinality/dimension mismatch")
    if any(len(row) != dimension or row[0] == 0 for row in rows):
        raise RuntimeError("invalid or unbounded square representation")
    return {tuple(v / row[0] for v in row) for row in rows}


def run(binary, input_file, work):
    completed = subprocess.run([str(binary), "-d", "--no-automorphisms",
                                "-i", str(input_file)], cwd=work,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="strict", timeout=60)
    print(completed.stdout, flush=True)
    if completed.returncode:
        raise RuntimeError("installed SymPol computation returned " + str(completed.returncode))
    return completed.stdout


def main():
    binary, root = map(Path, sys.argv[1:3])
    if not binary.is_file():
        raise RuntimeError("tested package executable absent")
    work = root / "鸿蒙 多面体往返"
    work.mkdir(parents=True, exist_ok=False)
    vertices = {(Fraction(1), Fraction(x), Fraction(y))
                for x in (-1, 1) for y in (-1, 1)}
    source = work / "正方形 顶点.ext"
    source.write_text("V-representation\nbegin\n4 3 rational\n" +
                      "".join(" ".join(map(str, row)) + "\n" for row in sorted(vertices)) +
                      "end\n", encoding="utf-8")
    inequalities = representation(run(binary, source, work), "H")
    expected = {(Fraction(1), Fraction(x), Fraction(y))
                for x, y in ((-1, 0), (1, 0), (0, -1), (0, 1))}
    if inequalities != expected:
        raise RuntimeError("computed facets do not describe the original square")
    dual = work / "正方形 半空间.ine"
    dual.write_text("H-representation\nbegin\n4 3 rational\n" +
                    "".join(" ".join(map(str, row)) + "\n" for row in sorted(inequalities)) +
                    "end\n", encoding="utf-8")
    recovered = representation(run(binary, dual, work), "V")
    if recovered != vertices:
        raise RuntimeError("V-to-H-to-V workflow changed the geometric result")
    print("SYMPOL_HARMONY_E2E_PASS=1/1 installed-cli utf8-space-path V-H-V exact-square", flush=True)


if __name__ == "__main__":
    main()
