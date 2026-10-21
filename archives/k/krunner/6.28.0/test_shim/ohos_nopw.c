/* getpwuid/getpwuid_r shim for the recipe's autotest session bus (LD_PRELOAD),
 * HarmonyOS PC.
 *
 * This is the same shim the dbus/1.14.10.3 test_package carries as
 * hos_nopw.c (verified on device there); it is vendored here because the
 * krunner upstream autotests need a real session D-Bus and this recipe
 * starts one with the dbus tool package.
 *
 * This device image runs the tests as uid 20020101, which has no /etc/passwd
 * entry: getpwuid() fails.  dbus-daemon resolves the passwd entry of a
 * connection's uid while completing EXTERNAL authentication, and without an
 * answer it logs
 *     Could not get password database information for UID of current process:
 *     User "???" unknown
 * and drops the connection (the client then just times out).
 *
 * Scope, stated exactly: the shim answers getpwuid/getpwuid_r that the
 * *daemon* makes.  It returns one fixed synthetic record for ANY uid (not
 * just the caller's own uid, and the record's name/home are constants).  It
 * does not and cannot forge the peer's identity: EXTERNAL compares the
 * numeric uid taken from the unix socket's SO_PEERCRED (kernel-provided).
 *
 * This file is part of the *test harness only*; the shipped krunner package
 * does not contain it and does not need it.
 */
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
    pw.pw_name = s_name;
    pw.pw_passwd = (char *)"";
    pw.pw_uid = uid;
    pw.pw_gid = uid;
    pw.pw_gecos = s_name;
    pw.pw_dir = s_home;
    pw.pw_shell = s_shell;
    return &pw;
}

int getpwuid_r(uid_t uid, struct passwd *result, char *buf, size_t buflen,
               struct passwd **res)
{
    /* +1: the three memcpys below write the strings with their NULs
     * (sizeof includes each terminator), and one more NUL terminates the
     * empty pw_passwd field written after them — without the +1 the guard
     * admits buflen == 44 and *p = 0 lands one byte past the buffer. */
    size_t need = sizeof(s_name) + sizeof(s_home) + sizeof(s_shell) + 1;
    char *p = buf;
    if (buflen < need) {
        if (res)
            *res = 0;
        return 34;
    }
    memcpy(p, s_name, sizeof(s_name));
    result->pw_name = p;
    p += sizeof(s_name);
    memcpy(p, s_home, sizeof(s_home));
    result->pw_dir = p;
    p += sizeof(s_home);
    memcpy(p, s_shell, sizeof(s_shell));
    result->pw_shell = p;
    p += sizeof(s_shell);
    result->pw_passwd = p;
    *p = 0;
    result->pw_uid = uid;
    result->pw_gid = uid;
    result->pw_gecos = result->pw_name;
    if (res)
        *res = result;
    return 0;
}
