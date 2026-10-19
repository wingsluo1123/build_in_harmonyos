import pathlib
import subprocess
import sys
import tempfile

binary = sys.argv[1]
with tempfile.TemporaryDirectory(prefix="ucg-consumer-") as root:
    source = pathlib.Path(root) / "sample.cpp"
    source.write_text("int Alpha = 17;\nint beta = 42;\n", encoding="utf-8")

    def check(name, options, rc, expected):
        result = subprocess.run([binary, "--noenv", "--jobs=1", *options],
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == rc, (name, result.returncode, result.stderr)
        assert expected in result.stdout, (name, result.stdout)
        print("CONSUMER", name, "PASS")

    check("installed version", ["--version"], 0, "0.3.3")
    check("literal search", ["Alpha", str(source)], 0, "int Alpha = 17;")
    check("regex search", ["beta.*42", str(source)], 0, "int beta = 42;")
    check("case insensitive", ["-i", "alpha", str(source)], 0, "int Alpha = 17;")
    check("no match", ["NeverPresent", str(source)], 1, "")
print("UCG_CONSUMER_RESULT=5/5")
