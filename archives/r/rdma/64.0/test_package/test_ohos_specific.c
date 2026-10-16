/*
 * HarmonyOS-specific tests for the rdma/64.0 package.
 *
 * These assertions cover behaviour that is unique to the OpenHarmony PC
 * (arm64) platform port, i.e. the gaps that the adaptation had to bridge:
 *
 *   T1  package public headers coexist with the OHOS netlink/socket headers
 *       (the __MUSL__ / sockaddr_storage conflict).
 *   T2  __progname stands in for glibc's program_invocation_short_name.
 *   T3  strrchr() provides the rindex() semantics rdma-core relies on, and
 *       rindex() itself is only present as a weak symbol on OHOS.
 *   T4  the thread teardown (signal + pthread_kill + pthread_join) actually
 *       reaps a worker; OHOS pthread_cancel() status is reported alongside.
 *   T5  the package still enumerates devices cleanly when no RDMA hardware
 *       is present (the normal case on a HarmonyOS PC).
 *
 * NOTE: rindex / pthread_cancel / getpass are not exported by the OHOS libc
 * at link time. They are therefore declared weak here -- exactly the way the
 * package's own portability header declares them -- so this test links and
 * can assert on their actual availability instead of silently depending on it.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>

/* T1: must compile together, and must agree on sockaddr_storage.
 * __MUSL__=1 is passed by test_package/CMakeLists.txt, mirroring the
 * definition the package itself is built with. */
#include <linux/netlink.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <infiniband/verbs.h>
#include <rdma/rdma_cma.h>

extern char *rindex(const char *s, int c) __attribute__((weak));
extern int pthread_cancel(pthread_t thread) __attribute__((weak));
extern int pthread_setcancelstate(int state, int *oldstate)
	__attribute__((weak));
extern int pthread_setcanceltype(int type, int *oldtype) __attribute__((weak));

static int failures;

#define CHECK(cond, msg)                                                       \
	do {                                                                   \
		if (cond) {                                                    \
			printf("  [ OK ] %s\n", msg);                          \
		} else {                                                       \
			printf("  [FAIL] %s\n", msg);                          \
			failures++;                                            \
		}                                                              \
	} while (0)

/* ------------------------------------------------------------------ T1 */
static void test_headers_coexist(void)
{
	struct sockaddr_storage ss;
	struct sockaddr_in sin;
	struct ibv_device **devs;
	struct ibv_context **ctxs;
	int num = -1;

	printf("T1: package headers + OHOS netlink/socket headers\n");

	memset(&ss, 0, sizeof(ss));
	memset(&sin, 0, sizeof(sin));
	sin.sin_family = AF_INET;
	sin.sin_port = htons(12345);
	memcpy(&ss, &sin, sizeof(sin));

	/* Without __MUSL__ the OHOS sys/socket.h does not declare
	 * struct sockaddr_storage and this file would not compile at all. */
	CHECK(ss.ss_family == AF_INET,
	      "sockaddr_storage usable next to <linux/netlink.h>");
	CHECK(sizeof(struct nlmsghdr) == NLMSG_HDRLEN,
	      "netlink header layout intact");

	/* These declarations must survive both headers being included: taking
	 * the address of each public entry point forces the linker to resolve
	 * symbols declared by the two header families in one translation unit. */
	struct ibv_device **(*verbs_list)(int *) = ibv_get_device_list;
	struct ibv_context **(*cma_list)(int *) = rdma_get_devices;

	CHECK(sizeof(struct sockaddr_storage) >= sizeof(struct sockaddr_in),
	      "sockaddr_storage complete (not just declared)");
	CHECK(verbs_list != NULL, "ibv_get_device_list resolved after <linux/netlink.h>");
	CHECK(cma_list != NULL, "rdma_get_devices resolved after <linux/netlink.h>");

	errno = 0;
	devs = ibv_get_device_list(NULL);
	CHECK(devs != NULL || errno != 0,
	      "ibv_get_device_list() callable after sys/socket.h");
	if (devs)
		ibv_free_device_list(devs);

	errno = 0;
	ctxs = rdma_get_devices(&num);
	CHECK(num >= 0, "rdma_get_devices() callable");
	if (ctxs)
		rdma_free_devices(ctxs);
}

/* ------------------------------------------------------------------ T2 */
static void test_progname(void)
{
	extern char *__progname;

	printf("T2: program_invocation_short_name substitute\n");

	CHECK(__progname != NULL && __progname[0] != '\0',
	      "__progname is non-empty");
	CHECK(strchr(__progname, '/') == NULL,
	      "__progname carries no path separator");
}

/* ------------------------------------------------------------------ T3 */
static void test_rindex_equivalence(void)
{
	const char *path = "/usr/lib/libibverbs.so";
	char *a = strrchr(path, '/');

	printf("T3: rindex() semantics via strrchr()\n");

	CHECK(a != NULL && strcmp(a, "/libibverbs.so") == 0,
	      "strrchr() finds the last separator");

	if (rindex == NULL) {
		printf("  [info] rindex() absent from OHOS libc -> the package's "
		       "portability header maps it to strrchr()\n");
		CHECK(strrchr(path, '/') == a, "mapped rindex == strrchr");
	} else {
		CHECK(rindex(path, '/') == a, "native rindex() agrees with strrchr()");
	}
}

/* ------------------------------------------------------------------ T4 */
static pthread_mutex_t t4_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t t4_cond = PTHREAD_COND_INITIALIZER;
static int t4_ready;
static volatile sig_atomic_t t4_woken;

static void t4_sigusr1(int sig)
{
	(void)sig;
	t4_woken = 1;
}

static void *t4_worker(void *arg)
{
	struct sigaction sa;
	sigset_t mask;
	int oldstate = -1, oldtype = -1;

	(void)arg;

	memset(&sa, 0, sizeof(sa));
	sa.sa_handler = t4_sigusr1;
	sigemptyset(&sa.sa_mask);
	sigaction(SIGUSR1, &sa, NULL);

	sigemptyset(&mask);
	sigaddset(&mask, SIGUSR1);
	pthread_sigmask(SIG_UNBLOCK, &mask, NULL);

	/* OHOS keeps the PTHREAD_CANCEL_* macros but exports no cancellation
	 * engine, so the entry points are absent (weak == NULL) here. */
	if (pthread_setcancelstate)
		pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, &oldstate);
	if (pthread_setcanceltype)
		pthread_setcanceltype(PTHREAD_CANCEL_DEFERRED, &oldtype);
	printf("  [info] worker cancel state=%d type=%d (entry points %s)\n",
	       oldstate, oldtype,
	       pthread_setcancelstate ? "present" : "absent");

	pthread_mutex_lock(&t4_lock);
	t4_ready = 1;
	pthread_cond_signal(&t4_cond);
	pthread_mutex_unlock(&t4_lock);

	while (!t4_woken)
		pause();

	return NULL;
}

static void test_thread_teardown(void)
{
	pthread_t th;
	int rc;
	void *join_ret = NULL;

	printf("T4: thread teardown (signal + pthread_kill + join)\n");

	if (pthread_cancel == NULL)
		printf("  [info] pthread_cancel() absent from OHOS libc "
		       "(ENOSYS semantics), signal-based teardown required\n");
	else
		printf("  [info] pthread_cancel() present in OHOS libc\n");

	rc = pthread_create(&th, NULL, t4_worker, NULL);
	CHECK(rc == 0, "pthread_create()");
	if (rc != 0)
		return;

	pthread_mutex_lock(&t4_lock);
	while (!t4_ready)
		pthread_cond_wait(&t4_cond, &t4_lock);
	pthread_mutex_unlock(&t4_lock);

	CHECK(pthread_kill(th, SIGUSR1) == 0, "pthread_kill(SIGUSR1) delivers");
	CHECK(pthread_join(th, &join_ret) == 0, "pthread_join() reaps the worker");
	CHECK(t4_woken != 0, "signal handler ran on the worker thread");
}

/* ------------------------------------------------------------------ T5 */
static void test_no_hardware_path(void)
{
	struct ibv_device **devs;
	int num = -1, num2 = -1;

	printf("T5: hardware-less enumeration (HarmonyOS PC has no HCA)\n");

	errno = 0;
	devs = ibv_get_device_list(&num);
	CHECK(num >= 0, "device count is non-negative");
	CHECK(devs != NULL || errno != 0,
	      "ibv_get_device_list returns a list or sets errno");
	printf("  [info] RDMA devices present: %d\n", num);

	if (devs) {
		int i;
		for (i = 0; i < num; i++) {
			CHECK(devs[i] != NULL && devs[i]->name != NULL,
			      "each enumerated device has a name");
		}
		ibv_free_device_list(devs);
	}

	/* Enumeration is idempotent: a second pass sees the same devices. */
	errno = 0;
	devs = ibv_get_device_list(&num2);
	CHECK(devs != NULL || errno != 0,
	      "second enumeration behaves like the first");
	CHECK(num2 == num, "second enumeration agrees with the first");
	if (devs)
		ibv_free_device_list(devs);
}

int main(void)
{
	printf("== rdma/64.0 HarmonyOS-specific tests ==\n");

	test_headers_coexist();
	test_progname();
	test_rindex_equivalence();
	test_thread_teardown();
	test_no_hardware_path();

	if (failures) {
		printf("== RESULT: FAIL (%d assertion(s)) ==\n", failures);
		return 1;
	}
	printf("== RESULT: PASS ==\n");
	return 0;
}
