#!/bin/sh
# Reproducible runner for the upstream dbus test suite on HarmonyOS PC (OHOS aarch64).
#
# Why a runner is needed at all (platform properties of this device image, recorded
# with the original errors; no test source or fixture is modified):
#   1. The sandbox UID (20020101) has no /etc/passwd entry:
#        dbus[...]: Could not get password database information for UID of current process
#      dbus-daemon hits this while completing EXTERNAL authentication and drops the
#      connection; the tiny getpwuid/getpwuid_r shim below (LD_PRELOAD for every test
#      binary, which act as client and/or daemon in one process) lets them get past it.
#      The shim returns one fixed synthetic record for ANY uid; it cannot forge peer
#      identity — auth compares the numeric uid from SO_PEERCRED (unix sockets).
#   2. /tmp is a read-only erofs mount:
#        Failed to bind socket "/tmp/dbus-XXXX": Read-only file system   (errno 30)
#      The upstream fixtures hardcode unix:tmpdir=/tmp, so the cases that need a
#      pathname socket there cannot start their private bus; they are reported failed
#      with that reason. Pathname AF_UNIX itself is available on this platform, just
#      not in /tmp — see the directory table in the PR notes.
#   2b. hmdfs refuses pathname AF_UNIX bind (EPERM), which matters where the tests
#      bind a *relative* socket path in their ctest working directory
#      (<build>/Release/bin, on hmdfs): test-misc-internals dies on
#        server listen error: ... Failed to bind socket "./boogie": Operation not
#        permitted
#      The el2 sandbox dirs accept the same bind (probe in the PR notes).
#   3. Three tests (test-fdpass, test-loopback, test-corrupt) start their own
#      in-process TCP server (tcp:host=127.0.0.1) and then hang under ctest.
#      Root cause, established with a verbose trace of this exact build plus a
#      same-source Linux build of the same suite:
#        - EXTERNAL cannot authenticate over TCP anywhere: the server finds no
#          socket peer credentials and answers REJECTED EXTERNAL DBUS_COOKIE_SHA1
#          ANONYMOUS.  The identical rejection appears on Linux (a getsockopt
#          probe there also returns uid=(uid_t)-1 for TCP).
#        - The client then tries DBUS_COOKIE_SHA1, which needs a keyring directory
#          whose stat owner equals the process uid.  dbus's CMake pins
#          DBUS_TEST_HOMEDIR to <build>/Release/dbus (CTest Environment property),
#          and that tree lives on hmdfs, which reports uid 20001006 for every
#          file regardless of who created it (verified: a file written by this
#          process also stats as 20001006).  The keyring check therefore fails,
#          the connection is dropped, and the test spins until glib's watchdog
#          (Bail out! Test timed out (SIGALRM received)).
#        - Proof of the mechanism: the same binaries, invoked directly (bypassing
#          the ctest-pinned home) with DBUS_TEST_HOMEDIR on an el2 sandbox dir —
#          a filesystem that preserves the real uid — pass their TCP cases
#          (loopback /connect/tcp, /connect/nonce-tcp, corrupt /corrupt/tcp).
#          What still fails for them then is the read-only-/tmp cases, the same
#          limitation as note 2.  The ctest registration stays the accounting
#          unit, so these three remain counted as failed with this explanation;
#          the direct run is evidence, not a recount.
#
# Usage:  test_upstream.sh <build_tree> [outdir]
#   <build_tree>  a configured dbus build tree (bin/, lib/, test/) as produced by the recipe
#   [outdir]      where logs land (default: $PWD/dbus-upstream-run)
#
# Exit status: 0 only if every registered test passed.
set -u

TREE=${1:?usage: test_upstream.sh <build_tree> [outdir]}
OUT=${2:-$PWD/dbus-upstream-run}
BIN="$TREE/bin"
CC=${CC:-/data/service/hnp/bin/clang}

mkdir -p "$OUT" "$OUT/logs"

# Note on DBUS_TEST_HOMEDIR: the generated CTest configuration already pins it
# to <build>/Release/dbus via the ENVIRONMENT property, which overrides anything
# exported here — so the runner does not set it.  See note 3 above for why that
# pinned home (on hmdfs) makes the three TCP cases fail.  For the direct-run
# evidence, invoke the binaries yourself with:
#   DBUS_TEST_HOMEDIR=/data/storage/el2/base/tmp/<somewhere-you-own> ./bin/test-loopback

# ---- getpwuid shim ----------------------------------------------------------
cat > "$OUT/pwd_shim.c" <<'SHIM'
#define _GNU_SOURCE
#include <pwd.h>
#include <string.h>
#include <sys/types.h>
static char s_name[] = "ohosuser";
static char s_home[] = "/storage/Users/currentUser";
static char s_shell[] = "/bin/sh";
struct passwd *getpwuid(uid_t uid)
{
    static struct passwd pw;
    pw.pw_name = s_name; pw.pw_passwd = (char *)""; pw.pw_uid = uid; pw.pw_gid = uid;
    pw.pw_gecos = s_name; pw.pw_dir = s_home; pw.pw_shell = s_shell;
    return &pw;
}
int getpwuid_r(uid_t uid, struct passwd *result, char *buf, size_t buflen, struct passwd **res)
{
    size_t need = sizeof(s_name) + sizeof(s_home) + sizeof(s_shell);
    if (buflen < need) { if (res) *res = 0; return 34; }
    char *p = buf;
    memcpy(p, s_name, sizeof(s_name));   result->pw_name = p; p += sizeof(s_name);
    memcpy(p, s_home, sizeof(s_home));   result->pw_dir = p;  p += sizeof(s_home);
    memcpy(p, s_shell, sizeof(s_shell)); result->pw_shell = p; p += sizeof(s_shell);
    result->pw_passwd = p; *p = 0;
    result->pw_uid = uid; result->pw_gid = uid; result->pw_gecos = result->pw_name;
    if (res) *res = result;
    return 0;
}
SHIM
"$CC" -shared -fPIC -o "$OUT/libnopw.so" "$OUT/pwd_shim.c" || exit 2

# ---- run --------------------------------------------------------------------
echo "build tree : $TREE"
echo "output dir : $OUT"
echo "shim       : $OUT/libnopw.so"
cd "$TREE" || exit 2

LD_PRELOAD="$OUT/libnopw.so" \
LD_LIBRARY_PATH="$TREE/lib:${LD_LIBRARY_PATH:-}" \
ctest -j1 --output-on-failure > "$OUT/ctest-run.log" 2>&1
rc=$?

# ---- per-test summary (name, result, TAP plan, ok/not-ok, first error) -------
python3 - "$OUT/ctest-run.log" "$OUT/summary.tsv" <<'PY'
import re, sys
log, out = sys.argv[1], sys.argv[2]
t = open(log, encoding="utf-8", errors="replace").read()
rows = []
for b in re.split(r"\n(?=\s*\d+/\d+ Test\s+#)", t):
    m = re.match(r"\s*\d+/\d+ Test\s+#(\d+): (\S+)\s+\.*\s*(.*)", b, re.S)
    if not m:
        continue
    name = m.group(2)
    head = b.splitlines()[0]
    res = "Passed" if "Passed" in head else ("Failed" if ("Failed" in head or "Exception" in head or "abort" in head) else "?")
    plan = re.search(r"^1\.\.(\d+)", b, re.M)
    oks = len(re.findall(r"^ok ", b, re.M))
    nok = len(re.findall(r"^not ok ", b, re.M))
    err = ""
    for l in b.splitlines():
        if re.search(r"ERROR:|FATAL-ERROR|assertion failed|Failed to bind|AccessDenied|Bail out|Could not", l):
            err = l.strip()[:160]
            break
    rows.append((name, res, plan.group(1) if plan else "", oks, nok, err))
with open(out, "w", encoding="utf-8") as fh:
    fh.write("test\tresult\ttap_plan\tok\tnot_ok\tfirst_error\n")
    for r in rows:
        fh.write("%s\t%s\t%s\t%d\t%d\t%s\n" % r)
passed = sum(1 for r in rows if r[1] == "Passed")
print("registered tests : %d" % len(rows))
print("passed           : %d" % passed)
print("failed           : %d" % (len(rows) - passed))
print("summary          : %s" % out)
PY

echo "ctest exit : $rc   (full log: $OUT/ctest-run.log)"
exit $rc
