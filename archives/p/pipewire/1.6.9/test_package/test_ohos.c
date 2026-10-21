/* test_ohos.c — HarmonyOS consumer validation for the pipewire package.
 *
 * Runs against the packaged (installed) artifacts, the same way a real
 * consumer such as kpipewire uses them:
 *  1. pw_mempool memfd mapping (OHOS memfd denies fstat(); pipewire falls
 *     back to the known block size for the bounds check).
 *  2. pw_mempool import mapping: a memfd imported from another pool has no
 *     local size, so the fstat() fallback must derive it from the fd
 *     (lseek); this is the protocol-native MemFd sharing path.
 *  3. pw_data_loop cancel fallback (OHOS libc has no pthread_cancel();
 *     pipewire wakes the loop through pw_loop_invoke() and the thread
 *     must exit through its normal cleanup so that join succeeds).
 *  4. Consumer flow over the packaged library: context + core connection,
 *     stream creation, property update and a core sync round-trip. The
 *     core comes from pw_context_connect_self() (the in-process graph API
 *     used by the upstream examples and tests).
 *  5. Executing the packaged daemon (`bin/pipewire --version`). This is not
 *     skippable: it is the only case that runs a packaged ELF, so a signed-
 *     ELF integrity failure (execve EPERM) is caught even on devices where
 *     no AF_UNIX-bindable runtime directory is found.
 *  6. When the test harness finds a filesystem location that accepts an
 *     AF_UNIX bind (HMDFS rejects bind with EPERM), the packaged pipewire
 *     daemon is started there and the same consumer flow runs over
 *     protocol-native against that daemon. Without such a location this
 *     case is reported as SKIP, the library flow above still runs.
 *
 * Every case reports TEST PASS / TEST FAIL (SKIP for case 6 when needed)
 * and the program ends with a TEST SUMMARY line; any failure exits 1.
 */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include <pipewire/pipewire.h>
#include <spa/buffer/buffer.h>

static int test_mempool_memfd_map(void)
{
	long page_size = sysconf(_SC_PAGESIZE);
	struct pw_mempool *p;
	struct pw_memblock *b;
	struct pw_memmap *m1;

	if (page_size <= 0)
		return -1;

	p = pw_mempool_new(NULL);
	if (p == NULL)
		return -1;

	b = pw_mempool_alloc(p, PW_MEMBLOCK_FLAG_READWRITE, SPA_DATA_MemFd,
			     2 * page_size);
	if (b == NULL || b->fd < 0) {
		pw_mempool_destroy(p);
		return -1;
	}

	/* Map with a non-page-aligned offset: exercises the bounds check
	 * that falls back to the block size when fstat() is denied. */
	m1 = pw_mempool_map_id(p, b->id, PW_MEMMAP_FLAG_READWRITE,
			       page_size / 2, page_size, NULL);
	if (m1 == NULL || m1->ptr == NULL) {
		pw_mempool_destroy(p);
		return -1;
	}
	/* Round-trip a byte through the mapping. */
	((char *)m1->ptr)[0] = 0x5a;
	if (((char *)m1->ptr)[0] != 0x5a) {
		pw_memmap_free(m1);
		pw_mempool_destroy(p);
		return -1;
	}

	pw_memmap_free(m1);
	pw_mempool_destroy(p);
	return 0;
}

/* Map a memfd imported from another pool. pw_mempool_import() does not
 * record the block size locally, so the OHOS fstat() fallback must derive
 * it from the fd (lseek) instead. This is the path protocol-native uses
 * when a client and the daemon share a MemFd buffer. */
static int test_mempool_import_map(void)
{
	long page_size = sysconf(_SC_PAGESIZE);
	struct pw_mempool *p1, *p2;
	struct pw_memblock *b, *ib;
	struct pw_memmap *m;
	int fd, res = -1;

	if (page_size <= 0)
		return -1;
	p1 = pw_mempool_new(NULL);
	p2 = pw_mempool_new(NULL);
	if (p1 == NULL || p2 == NULL) {
		if (p1 != NULL)
			pw_mempool_destroy(p1);
		if (p2 != NULL)
			pw_mempool_destroy(p2);
		return -1;
	}
	b = pw_mempool_alloc(p1, PW_MEMBLOCK_FLAG_READWRITE, SPA_DATA_MemFd,
			     2 * page_size);
	if (b == NULL || b->fd < 0)
		goto out_pools;
	fd = dup(b->fd);
	if (fd < 0)
		goto out_pools;
	ib = pw_mempool_import(p2, PW_MEMBLOCK_FLAG_READWRITE, SPA_DATA_MemFd, fd);
	if (ib == NULL) {
		close(fd);
		goto out_pools;
	}
	m = pw_memblock_map(ib, PW_MEMMAP_FLAG_READWRITE,
			    page_size / 2, page_size, NULL);
	if (m != NULL) {
		if (m->ptr != NULL) {
			((char *)m->ptr)[0] = 0x36;
			if (((char *)m->ptr)[0] == 0x36)
				res = 0;
		}
		pw_memmap_free(m);
	}
out_pools:
	pw_mempool_destroy(p2);
	pw_mempool_destroy(p1);
	return res;
}

static int test_data_loop_cancel(void)
{
	struct pw_data_loop *dl;
	struct pw_loop *l;

	/* loop.cancel=true enables the cancellation path. OHOS libc has no
	 * pthread_cancel(); pipewire instead wakes the loop with
	 * pw_loop_invoke(do_stop) so the thread exits through its normal
	 * cleanup (no signal handler, no pthread_exit on musl). */
	dl = pw_data_loop_new(&(const struct spa_dict) {
		.n_items = 1,
		.items = (struct spa_dict_item[]) {
			{ PW_KEY_LOOP_CANCEL, "true" },
		},
	});
	if (dl == NULL)
		return -1;
	l = pw_data_loop_get_loop(dl);
	if (l == NULL) {
		pw_data_loop_destroy(dl);
		return -1;
	}
	if (pw_data_loop_start(dl) < 0) {
		pw_data_loop_destroy(dl);
		return -1;
	}
	/* Stop must wake + join the loop thread; the stop result is the
	 * observable outcome of the no-pthread_cancel path. */
	if (pw_data_loop_stop(dl) < 0) {
		pw_data_loop_destroy(dl);
		return -1;
	}
	pw_data_loop_destroy(dl);
	return 0;
}

struct core_sync {
	volatile int done;
};

static void on_core_done(void *data, uint32_t id, int seq)
{
	struct core_sync *sync = data;
	(void)id;
	(void)seq;
	sync->done = 1;
}

/* Real consumer flow: create a stream on the core, update its properties,
 * then perform a core sync round-trip so the request has gone through the
 * full protocol path and back. */
static int consumer_flow(struct pw_main_loop *ml, struct pw_core *core)
{
	static const struct pw_core_events core_events = {
		PW_VERSION_CORE_EVENTS,
		.done = on_core_done,
	};
	struct spa_dict_item items[] = {
		{ "consumer", "test_ohos" },
	};
	struct spa_dict props = SPA_DICT_INIT_ARRAY(items);
	struct core_sync sync = { 0 };
	struct spa_hook listener;
	struct pw_stream *stream;
	struct pw_loop *loop;
	int i;

	stream = pw_stream_new(core, "consumer-e2e", NULL);
	if (stream == NULL)
		return -1;
	if (pw_stream_update_properties(stream, &props) < 0) {
		pw_stream_destroy(stream);
		return -1;
	}

	spa_zero(listener);
	pw_core_add_listener(core, &listener, &core_events, &sync);
	if (pw_core_sync(core, PW_ID_CORE, 0) < 0) {
		spa_hook_remove(&listener);
		pw_stream_destroy(stream);
		return -1;
	}
	loop = pw_main_loop_get_loop(ml);
	for (i = 0; i < 50 && !sync.done; i++)
		pw_loop_iterate(loop, 100);
	/* The hook lives on this stack frame; detach it before returning so the
	 * core's hook list does not reference reclaimed stack memory. */
	spa_hook_remove(&listener);
	pw_stream_destroy(stream);
	return sync.done ? 0 : -1;
}

static int test_consumer_self_connect(void)
{
	struct pw_main_loop *ml;
	struct pw_context *ctx;
	struct pw_core *core;
	int res = -1;

	ml = pw_main_loop_new(NULL);
	if (ml == NULL)
		return -1;
	ctx = pw_context_new(pw_main_loop_get_loop(ml), NULL, 0);
	if (ctx == NULL) {
		pw_main_loop_destroy(ml);
		return -1;
	}
	core = pw_context_connect_self(ctx, NULL, 0);
	if (core != NULL && consumer_flow(ml, core) == 0)
		res = 0;
	pw_context_destroy(ctx);
	pw_main_loop_destroy(ml);
	return res;
}

static int wait_for_socket(const char *path, int tries)
{
	int i;

	for (i = 0; i < tries; i++) {
		if (access(path, F_OK) == 0)
			return 0;
		usleep(100000);
	}
	return -1;
}

/* Wait for a child with a deadline. Returns the wait status, or -1 when the
 * child had to be killed after not exiting within timeout_ms. SIGTERM is
 * tried first, SIGKILL after a 2s grace period; the child is always reaped. */
static int wait_child(pid_t pid, int timeout_ms)
{
	int i, status;

	for (i = 0; i < timeout_ms / 100; i++) {
		pid_t r = waitpid(pid, &status, WNOHANG);
		if (r == pid)
			return status;
		if (r < 0 && errno != EINTR)
			return -1;
		usleep(100000);
	}
	if (kill(pid, SIGTERM) < 0 && errno != ESRCH)
		fprintf(stderr, "kill(%ld, SIGTERM): %s\n", (long)pid, strerror(errno));
	for (i = 0; i < 20; i++) {
		pid_t r = waitpid(pid, &status, WNOHANG);
		if (r == pid)
			return -1;
		usleep(100000);
	}
	if (kill(pid, SIGKILL) < 0 && errno != ESRCH)
		fprintf(stderr, "kill(%ld, SIGKILL): %s\n", (long)pid, strerror(errno));
	while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
		;
	return -1;
}

/* Resolve the packaged daemon path and verify it is executable. PIPEWIRE_BIN_DIR
 * is always exported by the test harness, so a missing tree is a packaging
 * failure (hard error), never a platform-capability SKIP. */
static const char *daemon_path(char *buf, size_t size)
{
	const char *bin_dir = getenv("PIPEWIRE_BIN_DIR");

	if (bin_dir == NULL || bin_dir[0] == '\0') {
		fprintf(stderr, "PIPEWIRE_BIN_DIR is not set (packaged bin/ tree missing)\n");
		return NULL;
	}
	snprintf(buf, size, "%s/pipewire", bin_dir);
	if (access(buf, X_OK) != 0) {
		fprintf(stderr, "packaged daemon %s is missing or not executable: %s\n",
			buf, strerror(errno));
		return NULL;
	}
	return buf;
}

/* Non-skippable smoke case: actually execute the packaged daemon. On OHOS a
 * signed ELF whose bytes were rewritten during install fails execve with
 * EPERM, so this catches a broken package even when no AF_UNIX-bindable
 * runtime directory is available. */
static int test_daemon_exec_smoke(void)
{
	char daemon[600];
	pid_t pid;
	int status;

	if (daemon_path(daemon, sizeof(daemon)) == NULL)
		return -1;
	pid = fork();
	if (pid < 0) {
		fprintf(stderr, "fork: %s\n", strerror(errno));
		return -1;
	}
	if (pid == 0) {
		execl(daemon, daemon, "--version", (char *)NULL);
		fprintf(stderr, "exec %s: %s\n", daemon, strerror(errno));
		_exit(127);
	}
	status = wait_child(pid, 30000);
	if (status < 0) {
		fprintf(stderr, "%s --version did not exit in time\n", daemon);
		return -1;
	}
	if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
		fprintf(stderr, "%s --version exited with status 0x%x\n", daemon, status);
		return -1;
	}
	return 0;
}

static int test_daemon_client_e2e(void)
{
	const char *conf_dir = getenv("PIPEWIRE_CONFIG_DIR");
	const char *tmp_dir = getenv("PIPEWIRE_E2E_TMP");
	char runtime[512], daemon[600], socket_path[600], lock_path[608];
	struct pw_main_loop *ml = NULL;
	struct pw_context *ctx = NULL;
	struct pw_core *core = NULL;
	pid_t pid;
	int connected = 0;

	/* The executable check runs before the SKIP decision so that a missing
	 * or non-executable packaged daemon is always a hard failure. Only the
	 * absence of an AF_UNIX-bindable runtime dir is a SKIP (HMDFS rejects
	 * bind() with EPERM). */
	if (daemon_path(daemon, sizeof(daemon)) == NULL)
		return -1;
	if (tmp_dir == NULL || tmp_dir[0] == '\0')
		return 1; /* reported as SKIP */

	snprintf(runtime, sizeof(runtime), "%s/pw-e2e-XXXXXX", tmp_dir);
	if (mkdtemp(runtime) == NULL) {
		fprintf(stderr, "mkdtemp(%s): %s\n", runtime, strerror(errno));
		return -1;
	}
	setenv("PIPEWIRE_RUNTIME_DIR", runtime, 1);
	setenv("XDG_RUNTIME_DIR", runtime, 1);
	if (conf_dir != NULL)
		setenv("PIPEWIRE_CONFIG_DIR", conf_dir, 1);
	snprintf(socket_path, sizeof(socket_path), "%s/pipewire-0", runtime);

	pid = fork();
	if (pid < 0) {
		fprintf(stderr, "fork: %s\n", strerror(errno));
		if (rmdir(runtime) < 0)
			fprintf(stderr, "rmdir(%s): %s\n", runtime, strerror(errno));
		return -1;
	}
	if (pid == 0) {
		execl(daemon, daemon, (char *)NULL);
		fprintf(stderr, "exec %s: %s\n", daemon, strerror(errno));
		_exit(127);
	}

	if (wait_for_socket(socket_path, 50) < 0) {
		fprintf(stderr, "daemon socket %s did not appear\n", socket_path);
		goto out;
	}

	ml = pw_main_loop_new(NULL);
	ctx = ml != NULL ? pw_context_new(pw_main_loop_get_loop(ml), NULL, 0)
			 : NULL;
	core = ctx != NULL ? pw_context_connect(ctx, NULL, 0) : NULL;
	if (core != NULL && consumer_flow(ml, core) == 0)
		connected = 1;
out:
	if (ctx != NULL)
		pw_context_destroy(ctx);
	if (ml != NULL)
		pw_main_loop_destroy(ml);
	if (kill(pid, SIGTERM) < 0 && errno != ESRCH)
		fprintf(stderr, "kill(%ld, SIGTERM): %s\n", (long)pid, strerror(errno));
	if (wait_child(pid, 10000) < 0)
		fprintf(stderr, "daemon %ld did not exit within 10s\n", (long)pid);
	unlink(socket_path);
	/* The daemon keeps a lock file next to the socket
	 * (module-protocol-native: LOCK_SUFFIX ".lock"); remove it too so the
	 * temporary runtime directory can be deleted completely. */
	snprintf(lock_path, sizeof(lock_path), "%s.lock", socket_path);
	unlink(lock_path);
	if (rmdir(runtime) < 0)
		fprintf(stderr, "rmdir(%s): %s\n", runtime, strerror(errno));
	return connected ? 0 : -1;
}

struct test_case {
	const char *name;
	int (*fn)(void);
};

int main(void)
{
	static const struct test_case cases[] = {
		{ "mempool_memfd_map", test_mempool_memfd_map },
		{ "mempool_import_map", test_mempool_import_map },
		{ "data_loop_cancel", test_data_loop_cancel },
		{ "consumer_self_connect", test_consumer_self_connect },
		{ "daemon_exec_smoke", test_daemon_exec_smoke },
		{ "daemon_client_e2e", test_daemon_client_e2e },
	};
	int i, failed = 0, skipped = 0, passed = 0;

	pw_init(NULL, NULL);

	for (i = 0; i < (int)(sizeof(cases) / sizeof(cases[0])); i++) {
		int rc = cases[i].fn();

		if (rc == 0) {
			printf("TEST PASS: %s\n", cases[i].name);
			passed++;
		} else if (rc == 1) {
			printf("TEST SKIP: %s\n", cases[i].name);
			skipped++;
		} else {
			printf("TEST FAIL: %s\n", cases[i].name);
			failed++;
		}
	}

	pw_deinit();
	printf("TEST SUMMARY: %d passed, %d failed\n", passed, failed);
	if (skipped > 0)
		printf("TEST SKIPPED: %d\n", skipped);
	return failed == 0 ? 0 : 1;
}
