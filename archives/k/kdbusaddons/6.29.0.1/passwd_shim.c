/* Minimal passwd shim used only while the upstream test suite runs.
 *
 * The OHOS build sandbox UID has no /etc/passwd entry (getpwuid() returns
 * NULL).  Qt6DBus dlopen()s libdbus-1.so.3 at runtime and libdbus resolves
 * the effective user through getpwuid()/getpwuid_r() while attaching to a
 * session bus; when that lookup fails the attachment is aborted and every
 * upstream autotest reports "DBus session bus not found" even though a bus is
 * running.  Preloading this shim supplies a synthetic passwd entry for the
 * current UID so the tests exercise the real D-Bus protocol instead of
 * tripping over a sandbox limitation.
 *
 * It is test-only machinery: it is compiled into a private .so inside the
 * build folder and never packaged or installed.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <pwd.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static struct passwd pw;
static char pw_name[64];
static char pw_dir[512];
static char pw_shell[64];
static int pw_ready;

static void fill_pw(void)
{
	if (pw_ready) {
		return;
	}
	uid_t uid = getuid();
	gid_t gid = getgid();

	snprintf(pw_name, sizeof(pw_name), "user%u", (unsigned)uid);
	snprintf(pw_dir, sizeof(pw_dir), "/tmp/user%u", (unsigned)uid);
	snprintf(pw_shell, sizeof(pw_shell), "/bin/sh");

	pw.pw_name = pw_name;
	pw.pw_passwd = (char *)"x";
	pw.pw_uid = uid;
	pw.pw_gid = gid;
	pw.pw_gecos = (char *)"sandbox user";
	pw.pw_dir = pw_dir;
	pw.pw_shell = pw_shell;
	pw_ready = 1;
}

struct passwd *getpwuid(uid_t uid)
{
	(void)uid;
	fill_pw();
	return &pw;
}

int getpwuid_r(uid_t uid, struct passwd *result, char *buf, size_t buflen,
	       struct passwd **out)
{
	size_t off = 0;
	size_t len;

	(void)uid;
	fill_pw();
	*result = pw;
	if (buf != NULL) {
		len = strlen(pw_name) + 1;
		if (off + len > buflen) {
			return ERANGE;
		}
		memcpy(buf + off, pw_name, len);
		result->pw_name = buf + off;
		off += len;

		len = strlen(pw_dir) + 1;
		if (off + len > buflen) {
			return ERANGE;
		}
		memcpy(buf + off, pw_dir, len);
		result->pw_dir = buf + off;
		off += len;

		len = strlen(pw_shell) + 1;
		if (off + len > buflen) {
			return ERANGE;
		}
		memcpy(buf + off, pw_shell, len);
		result->pw_shell = buf + off;
	}
	*out = result;
	return 0;
}
