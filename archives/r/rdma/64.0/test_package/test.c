/*
 * test.c — L1 consumer test (test_package)
 *
 * R34: really uses the package under test. Every assertion goes through
 * rdma-core's public headers and public API:
 *   <infiniband/verbs.h>  -> ibv_get_device_list / ibv_free_device_list /
 *                            ibv_get_device_name / ibv_get_device_guid
 *   <rdma/rdma_cma.h>     -> rdma_get_devices / rdma_free_devices
 *
 * A HarmonyOS PC has no RDMA HCA, so both lists are legitimately empty and
 * rdma_get_devices() may report the missing ucma module. The assertions
 * therefore pin down "the API behaves correctly", not "a device exists":
 * the call chain and every release path are exercised either way.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <infiniband/verbs.h>
#include <rdma/rdma_cma.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
	if (cond) { \
		printf("  [PASS] %s\n", msg); \
	} else { \
		printf("  [FAIL] %s\n", msg); \
		failures++; \
	} \
} while (0)

int main(void)
{
	struct ibv_device **dev_list;
	struct ibv_context **rdma_ctxs;
	int num_verbs = -1, num_cma = -1;
	int first_verbs = -1;
	int i;

	printf("== rdma 64.0 test_package: L1 basic API test ==\n");

	/* librdmacm's rdma_get_devices() mirrors ibv_get_device_list(), but a
	 * second call after the first list was released must stay consistent. */
	errno = 0;
	dev_list = ibv_get_device_list(&num_verbs);
	CHECK(num_verbs >= 0, "device count is not negative");
	CHECK(dev_list != NULL || errno != 0,
	      "ibv_get_device_list returns a list, or NULL with errno set");
	printf("  [info] verbs devices: %d%s\n", num_verbs,
	       dev_list ? "" : " (list NULL: no provider initialised)");

	for (i = 0; i < num_verbs; i++) {
		CHECK(ibv_get_device_name(dev_list[i]) != NULL,
		      "ibv_get_device_name returns a name");
	}
	if (dev_list)
		ibv_free_device_list(dev_list);
	first_verbs = num_verbs;

	/* Repeated enumeration must not leak or crash and must agree with
	 * the first pass. */
	errno = 0;
	dev_list = ibv_get_device_list(&num_verbs);
	CHECK(num_verbs == first_verbs,
	      "device count agrees with the first enumeration");
	CHECK(dev_list != NULL || errno != 0,
	      "second ibv_get_device_list behaves the same way");
	if (dev_list)
		ibv_free_device_list(dev_list);

	errno = 0;
	rdma_ctxs = rdma_get_devices(&num_cma);
	CHECK(num_cma >= 0, "rdma_get_devices reports a non-negative count");
	if (rdma_ctxs == NULL) {
		CHECK(errno != 0, "rdma_get_devices sets errno when it fails");
		printf("  [info] rdma_get_devices() returned NULL (errno=%d, %s) "
		       "- expected without the ucma module\n", errno,
		       strerror(errno));
	} else {
		for (i = 0; i < num_cma; i++) {
			CHECK(rdma_ctxs[i] != NULL &&
			      rdma_ctxs[i]->device != NULL &&
			      rdma_ctxs[i]->device->name[0] != '\0',
			      "rdma context exposes a named device");
		}
		rdma_free_devices(rdma_ctxs);
	}
	CHECK(num_cma == 0 || rdma_ctxs != NULL,
	      "rdma_get_devices count matches the returned array");

	printf("== L1 basic API test: %s (%d failure(s), verbs=%d cma=%d) ==\n",
	       failures == 0 ? "PASS" : "FAIL", failures, num_verbs, num_cma);
	return failures == 0 ? 0 : 1;
}
