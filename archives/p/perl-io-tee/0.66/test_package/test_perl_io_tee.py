import subprocess
import sys
import tempfile
import os


def main():
    perl = sys.argv[1]
    # Test: load IO::Tee, create a tee object writing to multiple files, verify output
    tmpdir = tempfile.mkdtemp(prefix="io_tee_test_")
    file1 = os.path.join(tmpdir, "out1.txt")
    file2 = os.path.join(tmpdir, "out2.txt")

    perl_code = (
        f"use IO::Tee; "
        f"use IO::File; "
        f"my $f1 = IO::File->new('>{file1}') or die $!; "
        f"my $f2 = IO::File->new('>{file2}') or die $!; "
        f"my $tee = IO::Tee->new($f1, $f2); "
        f"$tee->print('hello tee\n'); "
        f"$tee->close(); "
        f"close $f1; close $f2; "
        # Verify both files have the content
        f"open my $r1, '<', '{file1}' or die $!; "
        f"my $c1 = do {{ local $/; <$r1> }}; close $r1; "
        f"die 'file1 mismatch' unless $c1 eq 'hello tee\n'; "
        f"open my $r2, '<', '{file2}' or die $!; "
        f"my $c2 = do {{ local $/; <$r2> }}; close $r2; "
        f"die 'file2 mismatch' unless $c2 eq 'hello tee\n'; "
        f"die 'no version' unless $IO::Tee::VERSION; "
        f"print 'PASS: IO::Tee multiplex write ok (v' . $IO::Tee::VERSION . ')\\n'"
    )

    command = [perl, "-e", perl_code]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
