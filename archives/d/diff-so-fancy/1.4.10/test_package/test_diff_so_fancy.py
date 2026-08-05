#!/usr/bin/env python3
"""Test diff-so-fancy by piping diff output through it."""
import subprocess
import sys
import os
import tempfile


def main():
    exe = sys.argv[1]

    tmpdir = tempfile.mkdtemp()
    file_a = os.path.join(tmpdir, "a.txt")
    file_b = os.path.join(tmpdir, "b.txt")

    with open(file_a, "w") as f:
        f.write("line 1\nline 2\nline 3\n")

    with open(file_b, "w") as f:
        f.write("line 1\nline 2 modified\nline 3\nline 4\n")

    # Use unified diff format text directly (avoids dependency on diff command)
    diff_text = (
        f"--- {file_a}\n"
        f"+++ {file_b}\n"
        "@@ -1,3 +1,4 @@\n"
        " line 1\n"
        "-line 2\n"
        "+line 2 modified\n"
        " line 3\n"
        "+line 4\n"
    )

    fancy_result = subprocess.run(
        [exe],
        input=diff_text,
        capture_output=True,
        text=True,
        timeout=10,
    )

    output = fancy_result.stdout
    assert len(output) > 0, "diff-so-fancy produced no output"
    assert "line 2" in output, f"Expected 'line 2' in output, got: {output}"
    assert "modified" in output, f"Expected 'modified' in output, got: {output}"
    assert fancy_result.returncode == 0, f"diff-so-fancy exited with {fancy_result.returncode}"

    # Cleanup
    os.remove(file_a)
    os.remove(file_b)
    os.rmdir(tmpdir)

    print(f"PASS: diff-so-fancy correctly formatted diff output ({len(output)} bytes)")


if __name__ == "__main__":
    main()
