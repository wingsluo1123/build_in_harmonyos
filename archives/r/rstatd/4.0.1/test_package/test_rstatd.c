/*
 * rstatd 4.0.1 -- functional test for the rpc.rstatd daemon.
 *
 * The package installs three executables and no library, so this test drives
 * the daemon the way a deployed service is driven: it emulates what inetd
 * does (a connected UDP socket on file descriptor 0) and speaks ONC RPC/XDR
 * to it over the wire.  The protocol code here is written from rstat.x
 * rather than reusing the package's generated stubs, so a passing run is
 * real evidence that the daemon's wire format and its /proc collectors work,
 * not just that a stub compiled.
 *
 * Why inetd mode: rstat_main.c passes proto=IPPROTO_UDP to svc_register()
 * when it runs standalone, and TI-RPC's svc_register() then returns the
 * result of pmap_set(), so the standalone daemon refuses to start unless a
 * portmapper is reachable.  With a socket already on descriptor 0 the daemon
 * stays in inetd mode, passes proto=0 and skips the portmapper entirely.
 * That is also the mode rstatd is designed for under inetd/systemd socket
 * activation, so the test exercises the deployed code path.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* From the rstat protocol definition (rstat.x, program RSTATPROG). */
#define RSTATPROG          100001u
#define RSTATVERS_ORIG     1u
#define RSTATVERS_TIME     3u
#define RSTATVERS_USERS    5u
#define RSTATPROC_STATS    1u
#define RSTATPROC_HAVEDISK 2u
#define CPUSTATES 4
#define DK_NDRIVE  4
#define FSHIFT 8
#define FSCALE (1 << FSHIFT)

static int g_checks;
static int g_failed;

static void ok(int cond, const char *fmt, ...)
{
	va_list ap;
	g_checks++;
	printf("  [%s] ", cond ? "PASS" : "FAIL");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
	fflush(stdout);
	if (!cond)
		g_failed++;
}

static void info(const char *fmt, ...)
{
	va_list ap;
	printf("  ---- ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
	fflush(stdout);
}

static void die(const char *fmt, ...)
{
	va_list ap;
	printf("  [FATAL] ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
	fflush(stdout);
	exit(2);
}

/* -------------------------------------------------------------- rpc wire */

struct xdr_buf {
	unsigned char *p;
	size_t len;
	size_t cap;
};

static void xb_reset(struct xdr_buf *b)
{
	b->len = 0;
	free(b->p);
	b->p = NULL;
	b->cap = 0;
}

static void xb_put(struct xdr_buf *b, unsigned int v)
{
	unsigned char t[4];

	if (b->len + 4 > b->cap) {
		b->cap = (b->len + 4) * 2;
		b->p = realloc(b->p, b->cap);
		if (!b->p)
			die("out of memory");
	}
	t[0] = (unsigned char)(v >> 24);
	t[1] = (unsigned char)(v >> 16);
	t[2] = (unsigned char)(v >> 8);
	t[3] = (unsigned char)v;
	memcpy(b->p + b->len, t, 4);
	b->len += 4;
}

static unsigned int xb_get(struct xdr_buf *b, const char *what)
{
	unsigned int v;

	if (b->len + 4 > b->cap)
		die("XDR reply truncated while reading %s (%zu of %zu bytes decoded)",
		    what, b->len, b->cap);
	v = ((unsigned int)b->p[b->len] << 24) | ((unsigned int)b->p[b->len + 1] << 16) |
	    ((unsigned int)b->p[b->len + 2] << 8) | (unsigned int)b->p[b->len + 3];
	b->len += 4;
	return v;
}

/* An RPC call with AUTH_NULL credentials and no parameters. */
static void build_call(struct xdr_buf *b, unsigned int xid, unsigned int vers,
		       unsigned int proc)
{
	b->len = 0;
	xb_put(b, xid);
	xb_put(b, 0);			/* CALL */
	xb_put(b, 2);			/* RPC version */
	xb_put(b, RSTATPROG);
	xb_put(b, vers);
	xb_put(b, proc);
	xb_put(b, 0);			/* cred flavour AUTH_NONE */
	xb_put(b, 0);			/* cred body length */
	xb_put(b, 0);			/* verf flavour AUTH_NONE */
	xb_put(b, 0);			/* verf body length */
}

/*
 * One request/response exchange against a daemon started in inetd mode.
 *
 * child_fd stays open on this side; the daemon runs in a child process with
 * the connected socket on its descriptor 0.
 */
struct daemon {
	pid_t pid;
	int sock;				/* our client socket, bound to client_port */
	unsigned int daemon_port;			/* the daemon's UDP port */
	unsigned int client_port;
	struct sockaddr_in daemon_addr;
};

static void start_inetd_daemon(struct daemon *d, const char *daemon_path)
{
	int pfd[2];
	struct sockaddr_in me, peer;
	socklen_t slen;
	int cs;

	cs = socket(AF_INET, SOCK_DGRAM, 0);
	if (cs < 0)
		die("socket: %s", strerror(errno));
	memset(&me, 0, sizeof(me));
	me.sin_family = AF_INET;
	me.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	me.sin_port = 0;
	if (bind(cs, (struct sockaddr *)&me, sizeof(me)) < 0)
		die("bind(client): %s", strerror(errno));
	slen = sizeof(me);
	if (getsockname(cs, (struct sockaddr *)&me, &slen) < 0)
		die("getsockname(client): %s", strerror(errno));
	d->client_port = ntohs(me.sin_port);

	memset(&peer, 0, sizeof(peer));
	peer.sin_family = AF_INET;
	peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	peer.sin_port = htons(d->client_port);

	if (pipe(pfd) < 0)
		die("pipe: %s", strerror(errno));

	d->pid = fork();
	if (d->pid < 0)
		die("fork: %s", strerror(errno));
	if (d->pid == 0) {
		/* Child: play inetd.  Bind a fresh UDP port, hand the number back
		 * to the parent, connect the socket to the client's address and
		 * move it onto descriptor 0 so rpc.rstatd takes the inetd path. */
		struct sockaddr_in mine;
		unsigned short bound;
		int cs2;

		close(pfd[0]);
		cs2 = socket(AF_INET, SOCK_DGRAM, 0);
		if (cs2 < 0)
			_exit(120);
		memset(&mine, 0, sizeof(mine));
		mine.sin_family = AF_INET;
		mine.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
		mine.sin_port = 0;
		if (bind(cs2, (struct sockaddr *)&mine, sizeof(mine)) < 0)
			_exit(121);
		slen = sizeof(mine);
		if (getsockname(cs2, (struct sockaddr *)&mine, &slen) < 0)
			_exit(122);
		bound = ntohs(mine.sin_port);
		if (write(pfd[1], &bound, sizeof(bound)) != (ssize_t)sizeof(bound))
			_exit(123);
		close(pfd[1]);

		if (connect(cs2, (struct sockaddr *)&peer, sizeof(peer)) < 0)
			_exit(124);
		if (cs2 != 0 && dup2(cs2, 0) < 0)
			_exit(125);
		if (cs2 > 0)
			close(cs2);
		execl(daemon_path, "rpc.rstatd", (char *)NULL);
		_exit(127);
	}

	close(pfd[1]);
	{
		unsigned short bound = 0;
		if (read(pfd[0], &bound, sizeof(bound)) != (ssize_t)sizeof(bound))
			die("child never reported its UDP port");
		d->daemon_port = bound;
	}
	close(pfd[0]);

	/* The inetd child reports its port before it connects/dups/execs, so a
	 * child that dies in one of those steps is invisible from here: the
	 * first request would just time out with no explanation (that is exactly
	 * how CI build #85729 presented itself on the OHOS worker).  Give it a
	 * moment and reap it non-destructively; if it is already gone, say which
	 * step killed it instead of waiting 20 s for a reply that cannot come. */
	{
		int status = 0;
		int i;
		pid_t reaped = 0;
		for (i = 0; i < 30 && reaped == 0; i++) {
			reaped = waitpid(d->pid, &status, WNOHANG);
			if (reaped == 0)
				usleep(10000);
		}
		if (reaped == d->pid) {
			static const struct { int code; const char *what; } step[] = {
				{ 120, "socket(AF_INET, SOCK_DGRAM)" },
				{ 121, "bind() of the daemon-side UDP socket" },
				{ 122, "getsockname() of the daemon-side socket" },
				{ 124, "connect() to the client's address" },
				{ 125, "dup2(socket, 0)" },
				{ 127, "execl(rpc.rstatd)" },
			};
			int rc = WIFEXITED(status) ? WEXITSTATUS(status)
						   : 128 + WTERMSIG(status);
			const char *what = "unknown step (see the child's exit code)";
			size_t k;
			for (k = 0; k < sizeof(step) / sizeof(step[0]); k++)
				if (step[k].code == rc)
					what = step[k].what;
			die("inetd child exited before the first request: exit %d (%s)"
			    " -- rpc.rstatd never got a socket on descriptor 0",
			    rc, what);
		}
	}

	memset(&d->daemon_addr, 0, sizeof(d->daemon_addr));
	d->daemon_addr.sin_family = AF_INET;
	d->daemon_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	d->daemon_addr.sin_port = htons((unsigned short)d->daemon_port);

	{
		struct timeval tv;
		tv.tv_sec = 20;
		tv.tv_usec = 0;
		setsockopt(cs, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
	}
	d->sock = cs;
}

/* Wait for the inetd-mode daemon, which exits 0 once it has served a request. */
static int reap_daemon(struct daemon *d)
{
	int status = -1;
	int i;

	for (i = 0; i < 250; i++) {
		pid_t r = waitpid(d->pid, &status, WNOHANG);
		if (r == d->pid) {
			close(d->sock);
			return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
		}
		usleep(20000);
	}
	kill(d->pid, SIGKILL);
	waitpid(d->pid, &status, 0);
	close(d->sock);
	return -2;
}

static unsigned int get32_at(const unsigned char *p, size_t off)
{
	return ((unsigned int)p[off] << 24) | ((unsigned int)p[off + 1] << 16) |
	       ((unsigned int)p[off + 2] << 8) | (unsigned int)p[off + 3];
}

static void hexdump(const char *tag, const unsigned char *p, size_t n)
{
	size_t i;

	printf("  ---- %s (%zu bytes):", tag, n);
	for (i = 0; i < n && i < 32; i++)
		printf(" %02x", p[i]);
	printf("\n");
	fflush(stdout);
}

/*
 * Send one RPC call and read the reply.  Returns the accept_stat
 * (0 == SUCCESS); the decoded reply header is consumed, and whatever
 * follows it is left in *body.
 */
static int rpc_call(struct daemon *d, unsigned int xid, unsigned int vers,
		    unsigned int proc, struct xdr_buf *body, size_t *payload_len)
{
	struct xdr_buf msg;
	unsigned int accept, rstat;
	struct sockaddr_in from;
	socklen_t fromlen = sizeof(from);
	size_t off = 0;
	ssize_t n;

	xb_reset(body);
	memset(&msg, 0, sizeof(msg));
	build_call(&msg, xid, vers, proc);
	if (sendto(d->sock, msg.p, msg.len, 0, (struct sockaddr *)&d->daemon_addr,
		   sizeof(d->daemon_addr)) < 0)
		die("send: %s", strerror(errno));
	free(msg.p);

	body->cap = 8192;
	body->p = malloc(body->cap);
	if (!body->p)
		die("out of memory");
	n = recvfrom(d->sock, body->p, body->cap - 1, 0, (struct sockaddr *)&from,
		     &fromlen);
	if (n <= 0)
		die("recv: no reply from the daemon (%s)",
		    n == 0 ? "socket closed" : strerror(errno));
	body->len = (size_t)n;
	if (from.sin_addr.s_addr == htonl(INADDR_LOOPBACK) && from.sin_port != 0)
		info("reply came from 127.0.0.1:%u", ntohs(from.sin_port));

	/*
	 * ONC RPC over UDP frames the message with a record-marking header:
	 * a 32-bit word whose top bit marks the final fragment and whose
	 * remaining bits hold the fragment length.  Accept an unframed reply
	 * too, and report what actually arrived when neither shape matches.
	 */
	{
		int framed = 1;
		for (;;) {
			unsigned int w;

			if (off + 4 > body->len)
				break;
			w = get32_at(body->p, off);
			if (w & 0x80000000u) {		/* last fragment */
				size_t len = w & 0x7fffffffu;
				off += 4;
				if (len == 0 || off + len > body->len)
					break;
				body->cap = off + len;
				break;
			}
			if (w == 0) {			/* non-final fragment */
				off += 4;
				continue;
			}
			framed = 0;			/* no record marking at all */
			off = 0;
			break;
		}
		if (!framed)
			info("daemon reply carried no RPC record marking");
	}

	if (off + 28 > body->len) {
		hexdump("short reply", body->p, body->len);
		die("RPC reply too short: %zu bytes", body->len);
	}
	if (get32_at(body->p, off) != xid) {
		hexdump("unexpected reply", body->p, (size_t)n);
		die("reply xid mismatch (wanted 0x%08x)", xid);
	}
	/* Skip the xid we just matched; xb_get() reads from body->len. */
	body->len = off + 4;
	body->cap = (size_t)n;

	if (xb_get(body, "msg_type") != 1) {
		hexdump("not a REPLY", body->p, (size_t)n);
		die("not an RPC REPLY message");
	}
	rstat = xb_get(body, "reply_stat");
	(void)xb_get(body, "verf flavour");
	(void)xb_get(body, "verf length");
	accept = xb_get(body, "accept_stat");
	if (rstat != 0)
		die("RPC reply_stat=%u (MSG_DENIED)", rstat);
	/* everything past the fixed 24-byte RPC reply header is the result */
	if (payload_len)
		*payload_len = (size_t)n - off - 24;
	return (int)accept;
}

/* ------------------------------------------------------------ CLI helpers */

static int run_capture(const char *argv0, const char *arg, char *out, size_t outsz)
{
	int pfd[2];
	pid_t pid;
	int status = 0;
	ssize_t n;
	size_t used = 0;

	out[0] = '\0';
	if (pipe(pfd) < 0) {
		snprintf(out, outsz, "pipe: %s", strerror(errno));
		return -1;
	}
	pid = fork();
	if (pid < 0) {
		snprintf(out, outsz, "fork: %s", strerror(errno));
		close(pfd[0]);
		close(pfd[1]);
		return -1;
	}
	if (pid == 0) {
		char *args[3];

		close(pfd[0]);
		dup2(pfd[1], 1);
		dup2(pfd[1], 2);
		if (pfd[1] > 2)
			close(pfd[1]);
		args[0] = (char *)argv0;
		args[1] = (char *)arg;
		args[2] = NULL;
		execv(argv0, args);
		fprintf(stderr, "[test] execv(\"%s\") failed: %s\n", argv0, strerror(errno));
		_exit(127);
	}
	close(pfd[1]);
	while (used + 1 < outsz) {
		n = read(pfd[0], out + used, outsz - used - 1);
		if (n <= 0)
			break;
		used += (size_t)n;
	}
	out[used] = '\0';
	close(pfd[0]);
	{
		/* A regression that makes a client's getopt() loop spin forever
		 * (the -fno-signed-char trap) must fail, not hang the whole CI. */
		int waited = 0;
		while (waited < 30000) {
			if (waitpid(pid, &status, WNOHANG) == pid)
				break;
			usleep(1000);
			waited++;
		}
		if (waited >= 30000) {
			kill(pid, SIGKILL);
			waitpid(pid, &status, 0);
			return -3;			/* timed out */
		}
	}
	if (WIFEXITED(status))
		return WEXITSTATUS(status);
	return 128 + WTERMSIG(status);
}

/* --------------------------------------------------------------- the test */

int main(int argc, char **argv)
{
	const char *daemon = (argc > 1) ? argv[1] : "rpc.rstatd";
	const char *rup = (argc > 2) ? argv[2] : "rup";
	const char *rsysinfo = (argc > 3) ? argv[3] : "rsysinfo";
	char out[4096];
	int rc;

	printf("== rstatd 4.0.1 functional test (OHOS aarch64) ==\n");
	fflush(stdout);

	/* -- 1. the shipped clients must start and identify themselves ----- */
	printf("\n[1] shipped client binaries\n");
	rc = run_capture(rup, "-v", out, sizeof(out));
	ok(rc == 0, "rup -v exits 0 (got %d)", rc);
	ok(strstr(out, "rup version") != NULL,
	   "rup -v prints its version banner (%.50s)", out);

	rc = run_capture(rsysinfo, "-v", out, sizeof(out));
	ok(rc == 0, "rsysinfo -v exits 0 (got %d)", rc);
	ok(strstr(out, "rsysinfo version") != NULL,
	   "rsysinfo -v prints its version banner (%.50s)", out);

	/* -- 2. the client error path when nothing is listening -------------- */
	printf("\n[2] client error path with no rstatd reachable\n");
	rc = run_capture(rup, "127.0.0.1", out, sizeof(out));
	ok(rc != 0, "rup 127.0.0.1 fails when no rstatd answers (exit %d)", rc);
	ok(strstr(out, "RPC") != NULL || strstr(out, "rstatd") != NULL,
	   "rup explains the failure on stderr instead of exiting silently (%.60s)",
	   out);
	info("rup reported: %.90s", out);

	/* -- 3. RSTATVERS_USERS / RSTATPROC_STATS: the real payload ---------- */
	printf("\n[3] RPC RSTATVERS_USERS.RSTATPROC_STATS\n");
	{
		struct daemon d;
		struct xdr_buf body = {0};
		size_t plen = 0;
		unsigned int cp_time[CPUSTATES], dk_xfer[DK_NDRIVE];
		unsigned int v_pgpgin, v_pgpgout, v_pswpin, v_pswpout, v_intr, v_swtch, users;
		int if_ipackets, if_ierrors, if_oerrors, if_collisions, if_opackets;
		int avenrun[3];
		unsigned int boot_sec, boot_usec, cur_sec, cur_usec;
		unsigned int i;
		unsigned int cpu_total = 0;
		int j;

		start_inetd_daemon(&d, daemon);
		info("daemon pid=%d, daemon udp port=%u, client port=%u",
		     (int)d.pid, d.daemon_port, d.client_port);

		rc = rpc_call(&d, 0x2001, RSTATVERS_USERS, RSTATPROC_STATS, &body, &plen);
		ok(rc == 0, "daemon accepted RSTATPROC_STATS on RSTATVERS_USERS");
		if (rc == 0) {
			/* statsusers, in the field order declared by rstat.x */
			for (i = 0; i < CPUSTATES; i++)
				cp_time[i] = xb_get(&body, "cp_time");
			for (i = 0; i < DK_NDRIVE; i++)
				dk_xfer[i] = xb_get(&body, "dk_xfer");
			v_pgpgin  = xb_get(&body, "v_pgpgin");
			v_pgpgout = xb_get(&body, "v_pgpgout");
			v_pswpin  = xb_get(&body, "v_pswpin");
			v_pswpout = xb_get(&body, "v_pswpout");
			v_intr    = xb_get(&body, "v_intr");
			if_ipackets   = (int)xb_get(&body, "if_ipackets");
			if_ierrors    = (int)xb_get(&body, "if_ierrors");
			if_oerrors    = (int)xb_get(&body, "if_oerrors");
			if_collisions = (int)xb_get(&body, "if_collisions");
			v_swtch   = xb_get(&body, "v_swtch");
			for (j = 0; j < 3; j++)
				avenrun[j] = (int)xb_get(&body, "avenrun");
			boot_sec  = xb_get(&body, "boottime.tv_sec");
			boot_usec = xb_get(&body, "boottime.tv_usec");
			cur_sec   = xb_get(&body, "curtime.tv_sec");
			cur_usec  = xb_get(&body, "curtime.tv_usec");
			if_opackets = (int)xb_get(&body, "if_opackets");
			users       = xb_get(&body, "users");

			for (i = 0; i < CPUSTATES; i++)
				cpu_total += cp_time[i];

			info("cp_time = {%u,%u,%u,%u}", cp_time[0], cp_time[1], cp_time[2],
			     cp_time[3]);
			info("avenrun = {%d,%d,%d}  (FSCALE = 1<<%d)", avenrun[0], avenrun[1],
			     avenrun[2], FSHIFT);
			info("boottime = %u.%06u  curtime = %u.%06u", boot_sec, boot_usec,
			     cur_sec, cur_usec);
			info("paging: pgpgin=%u pgpgout=%u pswpin=%u pswpout=%u", v_pgpgin,
			     v_pgpgout, v_pswpin, v_pswpout);
			info("intr=%u swtch=%u users=%u", v_intr, v_swtch, users);
			info("net: ipkts=%d ierr=%d opkts=%d oerr=%d coll=%d", if_ipackets,
			     if_ierrors, if_opackets, if_oerrors, if_collisions);
			info("dk_xfer = {%u,%u,%u,%u}", dk_xfer[0], dk_xfer[1], dk_xfer[2],
			     dk_xfer[3]);

			ok(plen == 27 * 4,
			   "statsusers result is complete: 27 XDR words = %zu bytes", plen);
			ok(cpu_total > 0,
			   "cp_time read from /proc/stat is non-zero (total=%u jiffies)",
			   cpu_total);
			ok(avenrun[0] >= 0 && avenrun[1] >= 0 && avenrun[2] >= 0,
			   "avenrun holds a non-negative /proc/loadavg triple");
			ok(avenrun[0] < 1000 * FSCALE,
			   "avenrun[0] is a plausible fixed-point load average (%d < %d)",
			   avenrun[0], 1000 * FSCALE);
			ok(boot_sec > 0 && cur_sec > boot_sec,
			   "boottime (%u) precedes curtime (%u): /proc/uptime was read",
			   boot_sec, cur_sec);
			ok(cur_sec > 1600000000u,
			   "curtime is a plausible wall-clock timestamp (%u)", cur_sec);
			ok(v_intr > 0, "v_intr read from /proc/stat (=%u)", v_intr);
			ok(v_swtch > 0, "v_swtch (context switches) read from /proc/stat (=%u)",
			   v_swtch);
			ok(v_pgpgin > 0 && v_pgpgout > 0,
			   "page counters read from /proc/vmstat (in=%u out=%u)", v_pgpgin,
			   v_pgpgout);
			ok(if_ipackets >= 0 && if_ierrors >= 0 && if_opackets >= 0 &&
			   if_oerrors >= 0 && if_collisions >= 0,
			   "network counters read from /proc/net/dev are non-negative");
			ok(users < 1000000u,
			   "user count collected from the utmp file is sane (%u)", users);
			/* The 2.6+ /proc/diskstats collector must have run.  Had the
			 * daemon kept upstream's "should never be called" placeholder
			 * (which exit()s), this call would never have been answered.
			 *
			 * 2026-10-14（CI #90800）：旧断言写死 moved > 0，而 worker 的
			 * /proc/diskstats 里没有块设备（同一次运行里
			 * havedisk reports 0 disk(s)、dk_xfer={0,0,0,0} 都是 PASS），
			 * 于是「如实报 0」被判成「采集器坏了」。
			 * 现在与宿主 /proc/diskstats 的真实值对照，三个分支都可伪证：
			 *   ① 宿主文件不可读/无设备行 → 守护进程必须报 0
			 *   ② 宿主 sectors 总量为 0   → 守护进程必须报 0
			 *   ③ 宿主 sectors 总量 > 0   → 守护进程必须 >0 且不超过宿主总量
			 *      （dk_xfer 只有 DK_NDRIVE=4 个槽位、只统计它认得的设备行，
			 *        所以取值一定 <= 宿主全量；报得比宿主多就说明串位或造假）
			 */
			{
				unsigned int moved = 0;
				unsigned int host_sectors = 0;
				unsigned int host_devs = 0;
				FILE *ds = fopen("/proc/diskstats", "r");

				for (i = 0; i < DK_NDRIVE; i++)
					moved += dk_xfer[i];
				if (ds != NULL) {
					char dline[512];
					while (fgets(dline, sizeof(dline), ds) != NULL) {
						unsigned int f1, f2, f3;
						unsigned long long sec;
						/* sectors 是 /proc/diskstats 的第 6 个数值字段
						 * （内核 4.18+ 稳定；见 Documentation/admin-guide/iostats.rst） */
						if (sscanf(dline, "%u %u %*s %u %*u %llu",
						           &f1, &f2, &f3, &sec) == 4) {
							host_devs++;
							host_sectors += (unsigned int)sec;
						}
					}
					fclose(ds);
				}
				info("host /proc/diskstats: %u device lines, %u sectors total; "
				     "daemon reported %u over %d slots",
				     host_devs, host_sectors, moved, DK_NDRIVE);
				if (host_devs == 0 || host_sectors == 0) {
					ok(moved == 0,
					   "host /proc/diskstats has %u device line(s) / %u sectors, so the "
					   "daemon must report 0 and it did (no invented data)",
					   host_devs, host_sectors);
				} else {
					ok(moved > 0 && moved <= host_sectors,
					   "the /proc/diskstats collector reported %u sectors over %d slots, "
					   "within the host's %u sectors from %u device line(s)",
					   moved, DK_NDRIVE, host_sectors, host_devs);
				}
			}
		}
		free(body.p);
		rc = reap_daemon(&d);
		ok(rc == 0,
		   "inetd-mode daemon exits 0 after serving one request (got %d)", rc);
	}

	/* -- 4. RSTATVERS_USERS / RSTATPROC_HAVEDISK ------------------------ */
	printf("\n[4] RPC RSTATVERS_USERS.RSTATPROC_HAVEDISK\n");
	{
		struct daemon d;
		struct xdr_buf body = {0};
		size_t plen = 0;
		unsigned int have;

		start_inetd_daemon(&d, daemon);
		rc = rpc_call(&d, 0x2002, RSTATVERS_USERS, RSTATPROC_HAVEDISK, &body, &plen);
		ok(rc == 0, "daemon accepted RSTATPROC_HAVEDISK");
		if (rc == 0) {
			have = xb_get(&body, "havedisk");
			ok(plen == 4,
			   "havedisk result is exactly one u_int (%zu bytes)", plen);
			ok(have <= DK_NDRIVE,
			   "havedisk reports %u disk(s), within the protocol maximum of %d",
			   have, DK_NDRIVE);
		}
		free(body.p);
		rc = reap_daemon(&d);
		ok(rc == 0, "daemon exits 0 after the havedisk request (got %d)", rc);
	}

	/* -- 5. the other protocol versions must still be served -------------- */
	/*
	 * rstat_main.c registers its own hand written dispatcher (rstat_service in
	 * rstat_proc.c) for every version it knows, not the rpcgen-generated
	 * rstatprog_N functions, and rstat_service always serialises a
	 * RSTATPROC_STATS answer with xdr_statsusers.  So every version that is
	 * registered answers with the 27-word statsusers payload, and a version
	 * that was never registered is refused with PROG_UNAVAIL.
	 */
	printf("\n[5] other RSTAT protocol versions\n");
	{
		struct { unsigned int vers; int expect_ok; const char *label; } cases[] = {
			{ RSTATVERS_ORIG,  1, "RSTATVERS_ORIG  (1, struct stats)" },
			{ 2u,             1, "RSTATVERS_SWTCH (2, struct statsswtch)" },
			{ RSTATVERS_TIME,  1, "RSTATVERS_TIME  (3, struct statstime)" },
			{ 4u,             0, "RSTATVERS_VAR   (4) is not registered by rstat_main.c" },
		};
		size_t c;

		for (c = 0; c < sizeof(cases) / sizeof(cases[0]); c++) {
			struct daemon d;
			struct xdr_buf body = {0};
			size_t plen = 0;

			start_inetd_daemon(&d, daemon);
			rc = rpc_call(&d, 0x2100u + (unsigned)c, cases[c].vers,
				      RSTATPROC_STATS, &body, &plen);
			if (cases[c].expect_ok) {
				ok(rc == 0, "daemon served %s", cases[c].label);
				if (rc == 0) {
					unsigned int cp = 0;
					unsigned int i;
					ok(plen == 27 * 4,
					   "%s returned the 27-word statsusers payload (%zu bytes)",
					   cases[c].label, plen);
					for (i = 0; i < CPUSTATES; i++)
						cp += xb_get(&body, "cp_time");
					ok(cp > 0,
					   "%s carried a non-zero cp_time from /proc/stat (=%u)",
					   cases[c].label, cp);
				}
				rc = reap_daemon(&d);
				ok(rc == 0, "daemon exits 0 after %s (got %d)", cases[c].label, rc);
			} else {
				/* A refused request never reaches get_stats(), so the
				 * inetd one-shot alarm is never armed and the daemon keeps
				 * serving: assert it is still alive instead of expecting exit. */
				ok(rc == 2, "%s is refused with PROG_UNAVAIL (accept_stat=%d)",
				   cases[c].label, rc);
				/* waitpid(WNOHANG) == 0 proves the child has NOT exited.
				 * kill(pid, 0) would not: an unreaped zombie child still
				 * answers signal 0, and a daemon that crashed is exactly
				 * what this assertion has to catch. */
				sleep(1);
				ok(d.pid > 0 && waitpid(d.pid, NULL, WNOHANG) == 0,
				   "the daemon is still running (not exited, not a zombie) "
				   "after refusing %s", cases[c].label);
				kill(d.pid, SIGKILL);
				waitpid(d.pid, NULL, 0);
				close(d.sock);
			}
			free(body.p);
		}
	}

	/* -- 6. an unregistered program version must be refused --------------- */
	printf("\n[6] unregistered program version is refused\n");
	{
		struct daemon d;
		struct xdr_buf body = {0};
		size_t plen = 0;

		start_inetd_daemon(&d, daemon);
		rc = rpc_call(&d, 0x2200, 9u, RSTATPROC_STATS, &body, &plen);
		ok(rc == 2, "RSTATVERS 9 is rejected with accept_stat=%d (PROG_UNAVAIL)", rc);
		ok(body.cap >= 24, "the daemon still sent a well-formed RPC reply (%zu bytes)",
		   body.cap);
		sleep(1);
		ok(waitpid(d.pid, NULL, WNOHANG) == 0,
		   "a refused request does not terminate the daemon "
		   "(the child has not exited)");
		kill(d.pid, SIGKILL);
		waitpid(d.pid, NULL, 0);
		close(d.sock);
		free(body.p);
	}

	printf("\n== %d checks, %d failed ==\n", g_checks, g_failed);
	if (g_failed) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}
