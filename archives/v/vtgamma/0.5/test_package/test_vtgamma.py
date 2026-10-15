#!/usr/bin/env python3
import os, subprocess, sys

def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_FOLDER", "")
    perl_pkg = sys.argv[2] if len(sys.argv) > 2 else ""
    can_run = sys.argv[3] == "1" if len(sys.argv) > 3 else True
    script = os.path.join(pkg, "bin", "vtgamma")
    if not os.path.isfile(script):
        print(f"FAIL: vtgamma script not found at {script}")
        return 1
    print("OK: vtgamma script present at bin/vtgamma")
    with open(script, "r") as f:
        first_line = f.readline().strip()
    if first_line != "#!/usr/bin/env perl":
        print(f"FAIL: shebang is {first_line!r}, expected #!/usr/bin/env perl")
        return 1
    print("OK: shebang is #!/usr/bin/env perl")
    if not can_run:
        print("SKIP: perl -c (cross-building, cannot run target binary)")
        return 0
    perl_exe = os.path.join(perl_pkg, "bin", "perl") if perl_pkg else "perl"
    if not os.path.isfile(perl_exe) and perl_pkg:
        for cand in ("perl", "perl5.42.2"):
            c = os.path.join(perl_pkg, "bin", cand)
            if os.path.isfile(c):
                perl_exe = c
                break
    try:
        r = subprocess.run([perl_exe, "-c", script], capture_output=True, text=True, timeout=60)
        out = r.stdout or r.stderr or ""
        if r.returncode == 0 and "syntax OK" in out:
            print("OK: perl -c syntax OK")
        else:
            print(f"FAIL: perl -c rc={r.returncode}: {(out)[:200]}")
            return 1
    except FileNotFoundError:
        print(f"FAIL: perl not found ({perl_exe})")
        return 1
    except subprocess.TimeoutExpired:
        print("FAIL: perl -c timed out")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
