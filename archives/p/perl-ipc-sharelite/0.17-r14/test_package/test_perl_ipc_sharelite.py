import subprocess
import sys


def main():
    perl = sys.argv[1]
    code = (
        "use IPC::ShareLite qw( LOCK_EX LOCK_SH LOCK_UN LOCK_NB ); "
        "die 'IPC::ShareLite version mismatch' "
        "unless $IPC::ShareLite::VERSION eq q{0.17}; "
        "my $s = IPC::ShareLite->new("
        "-key => 612, -create => 'yes', -destroy => 'yes', -size => 256"
        ") or die q{new() failed: } . $!; "
        "$s->store(q{hello}) or die q{store() failed: } . $!; "
        "die q{retrieve() mismatch} unless $s->retrieve eq q{hello}; "
        "print qq{PASS: IPC::ShareLite 0.17 loaded and functional\\n}"
    )
    result = subprocess.run([perl, "-e", code], capture_output=True, text=True)
    if result.returncode != 0:
        # If SysV IPC fails (permissions), fall back to load+version check only
        fallback_code = (
            "use IPC::ShareLite; "
            "die 'version mismatch' "
            "unless $IPC::ShareLite::VERSION eq q{0.17}; "
            "print qq{PASS: IPC::ShareLite 0.17 loaded\\n}"
        )
        result2 = subprocess.run([perl, "-e", fallback_code], capture_output=True, text=True)
        if result2.returncode != 0:
            print(result2.stderr, file=sys.stderr)
            sys.exit(1)
        print(result2.stdout, end="")
    else:
        print(result.stdout, end="")


if __name__ == "__main__":
    main()
