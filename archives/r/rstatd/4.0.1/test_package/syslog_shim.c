/*
 * Diagnostic shim for the rstatd test_package (CI evidence gathering).
 *
 * Build #85828 showed the inetd child exiting 1 right after exec, and the
 * daemon's own error messages ("cannot create udp service." /
 * "unable to register (...)" / "cannot parse kernel release ...") all go
 * through syslog(), which is invisible on the CI worker.  When this object is
 * LD_PRELOADed it does two things:
 *
 *   1. replaces syslog() so every daemon diagnostic reaches stderr, which the
 *      conan test() log already captures;
 *   2. a constructor prints ground truth about the very state main() branches
 *      on: getsockname(0) (inetd vs standalone selection), the socket type of
 *      fd 0 and uname().release (patch 0003's kernel-version parse).
 *
 * It prints from every process it is injected into (the test harness, the
 * clients, the daemon); each line is prefixed so they can be told apart.
 * This shim is diagnostic-only: it does not alter return values, skip
 * assertions, or fake any evidence.
 */
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <syslog.h>
#include <unistd.h>

void syslog(int prio, const char *fmt, ...)
{
	va_list ap;

	fprintf(stderr, "[rstatd-syslog prio=%d] ", prio);
	va_start(ap, fmt);
	vfprintf(stderr, fmt, ap);
	va_end(ap);
	fputc('\n', stderr);
	fflush(stderr);
}

__attribute__((constructor)) static void fd0_probe(void)
{
	struct sockaddr_storage ss;
	struct { int code; const char *name; } famtab[] = {
		{ 0, "AF_UNSPEC" }, { 2, "AF_INET" }, { 10, "AF_INET6" },
		{ 1, "AF_LOCAL" },
	};
	const char *fam = "other";
	socklen_t slen = sizeof(ss);
	socklen_t tlen = sizeof(int);
	int type = 0;
	int r;
	size_t k;
	struct utsname { char release[65]; } u;
	long n;

	r = getsockname(0, (struct sockaddr *)&ss, &slen);
	for (k = 0; r == 0 && k < sizeof(famtab) / sizeof(famtab[0]); k++)
		if ((int)ss.ss_family == famtab[k].code)
			fam = famtab[k].name;
	fprintf(stderr, "[rstatd-probe pid=%ld] getsockname(0)=%d errno=%s family=%s",
		(long)getpid(), r, r ? strerror(errno) : "0", r ? "-" : fam);
	if (r == 0 && getsockopt(0, SOL_SOCKET, SO_TYPE, &type, &tlen) == 0)
		fprintf(stderr, " so_type=%s",
			type == 2 ? "SOCK_DGRAM" :
			type == 1 ? "SOCK_STREAM" : "(other)");
	/* minimal inline uname: uname(2) via syscall through stdio-free glibc
	 * is overkill here; read /proc/sys/kernel/osrelease instead, which the
	 * daemon's collectors already depend on being present. */
	{
		FILE *f = fopen("/proc/sys/kernel/osrelease", "r");
		if (f) {
			n = (long)fread(u.release, 1, sizeof(u.release) - 1, f);
			fclose(f);
			if (n > 0) {
				u.release[n] = '\0';
				for (k = 0; k < (size_t)n; k++)
					if (u.release[k] == '\n')
						u.release[k] = '\0';
				fprintf(stderr, " kernel.osrelease='%s'",
					u.release);
			}
		}
	}
	fputc('\n', stderr);
	fflush(stderr);
}
