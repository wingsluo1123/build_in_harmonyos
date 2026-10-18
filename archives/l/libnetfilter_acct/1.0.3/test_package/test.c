/* libnetfilter_acct 1.0.3 consumer test (Conan L1).
 *
 * Drives the installed public API end to end; nothing here needs a kernel
 * netlink round-trip, so the test is hermetic:
 *
 *   - object lifecycle:  nfacct_alloc / nfacct_free
 *   - attributes:        nfacct_attr_set_str / nfacct_attr_set_u64 /
 *                        nfacct_attr_set / nfacct_attr_unset /
 *                        nfacct_attr_get / nfacct_attr_get_str /
 *                        nfacct_attr_get_u64
 *   - netlink message:   nfacct_nlmsg_build_hdr / nfacct_nlmsg_build_payload /
 *                        nfacct_nlmsg_parse_payload  (serialise -> parse back)
 *   - rendering:         nfacct_snprintf (PLAIN and JSON)
 *
 * The build_payload -> parse_payload round-trip is the strongest check
 * available without privileges: the object is encoded into libmnl attributes
 * in network byte order and decoded back by the library itself, so an
 * attribute-coding or endianness regression fails here rather than in nfacct.
 *
 * OHOS note: the sysroot ships a bionic uapi <linux/socket.h> that
 * unconditionally defines struct sockaddr_storage, while musl <sys/socket.h>
 * defines its own copy.  The two headers share no guard macro (the musl side
 * has no _UAPI_LINUX_SOCKET_H), so both expand exactly once in *either*
 * include order -- reordering does not help.  Including <libmnl/libmnl.h>
 * below (needed for the nlmsghdr layout and mnl_nlmsg_size) pulls
 * <sys/socket.h> and then <linux/netlink.h> -> <linux/socket.h> into this
 * translation unit, so the redundant uapi copy is suppressed here and the one
 * typedef <linux/netlink.h> needs from it is supplied.
 */
#define _UAPI_LINUX_SOCKET_H
typedef unsigned short __kernel_sa_family_t;

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <libmnl/libmnl.h>
#include <linux/netfilter/nfnetlink.h>

#include <libnetfilter_acct/libnetfilter_acct.h>

#define ACCT_NAME "ohos-acct-smoke"
#define ACCT_PKTS 0x1122334455667788ULL
#define ACCT_BYTES 123456789012345ULL
#define ACCT_QUOTA 4096ULL
#define ACCT_SEQ 0x1234u

/* Number of CHECK() invocations in main(); verified at run time so the
 * accounting in MANIFEST.yml / notes.md cannot drift silently. */
#define N_ASSERT 24

static int checks;
static int fails;

#define CHECK(cond, ...)                              \
	do {                                          \
		checks++;                             \
		if (!(cond)) {                        \
			fprintf(stderr, "FAIL: ");    \
			fprintf(stderr, __VA_ARGS__); \
			fputc('\n', stderr);          \
			fails++;                      \
		}                                     \
	} while (0)

int main(void)
{
	char buf[512];
	struct nfacct *a, *b, *c;
	struct nlmsghdr *nlh;
	const uint32_t *flags;
	uint32_t quota_mode = NFACCT_F_QUOTA_PKTS;
	int ret;

	/* ---- 1. attribute round-trip on one object ---------------------- */
	a = nfacct_alloc();
	CHECK(a != NULL, "nfacct_alloc() returned NULL");
	if (a == NULL)
		return 1;

	nfacct_attr_set_str(a, NFACCT_ATTR_NAME, ACCT_NAME);
	nfacct_attr_set_u64(a, NFACCT_ATTR_PKTS, ACCT_PKTS);
	nfacct_attr_set_u64(a, NFACCT_ATTR_BYTES, ACCT_BYTES);
	nfacct_attr_set_u64(a, NFACCT_ATTR_QUOTA, ACCT_QUOTA);
	nfacct_attr_set(a, NFACCT_ATTR_FLAGS, &quota_mode);

	CHECK(nfacct_attr_get_str(a, NFACCT_ATTR_NAME) != NULL &&
	      strcmp(nfacct_attr_get_str(a, NFACCT_ATTR_NAME), ACCT_NAME) == 0,
	      "NFACCT_ATTR_NAME round-trip failed");
	CHECK(nfacct_attr_get_u64(a, NFACCT_ATTR_PKTS) == ACCT_PKTS,
	      "NFACCT_ATTR_PKTS round-trip: got %llu",
	      (unsigned long long)nfacct_attr_get_u64(a, NFACCT_ATTR_PKTS));
	CHECK(nfacct_attr_get_u64(a, NFACCT_ATTR_BYTES) == ACCT_BYTES,
	      "NFACCT_ATTR_BYTES round-trip: got %llu",
	      (unsigned long long)nfacct_attr_get_u64(a, NFACCT_ATTR_BYTES));
	CHECK(nfacct_attr_get_u64(a, NFACCT_ATTR_QUOTA) == ACCT_QUOTA,
	      "NFACCT_ATTR_QUOTA round-trip: got %llu",
	      (unsigned long long)nfacct_attr_get_u64(a, NFACCT_ATTR_QUOTA));
	CHECK(nfacct_attr_get(a, NFACCT_ATTR_FLAGS) != NULL,
	      "NFACCT_ATTR_FLAGS not reported as set");

	/* ---- 2. unset really clears an attribute ------------------------ */
	nfacct_attr_unset(a, NFACCT_ATTR_QUOTA);
	CHECK(nfacct_attr_get(a, NFACCT_ATTR_QUOTA) == NULL,
	      "nfacct_attr_unset() left NFACCT_ATTR_QUOTA set");
	nfacct_attr_set_u64(a, NFACCT_ATTR_QUOTA, ACCT_QUOTA);

	/* ---- 3. build the nfnetlink message for this object ------------- */
	nlh = nfacct_nlmsg_build_hdr(buf, NFNL_MSG_ACCT_NEW,
				     NLM_F_CREATE | NLM_F_ACK, ACCT_SEQ);
	CHECK(nlh != NULL, "nfacct_nlmsg_build_hdr() returned NULL");
	CHECK(nlh->nlmsg_type == ((NFNL_SUBSYS_ACCT << 8) | NFNL_MSG_ACCT_NEW),
	      "unexpected nlmsg_type 0x%x", (unsigned int)nlh->nlmsg_type);
	CHECK((nlh->nlmsg_flags & NLM_F_REQUEST) != 0,
	      "NLM_F_REQUEST not set on the built header (flags=0x%x)",
	      (unsigned int)nlh->nlmsg_flags);
	CHECK(nlh->nlmsg_seq == ACCT_SEQ, "unexpected nlmsg_seq %u",
	      (unsigned int)nlh->nlmsg_seq);

	nfacct_nlmsg_build_payload(nlh, a);

	/* ---- 4. parse it back into a fresh object ----------------------- */
	b = nfacct_alloc();
	CHECK(b != NULL, "second nfacct_alloc() returned NULL");
	if (b == NULL) {
		nfacct_free(a);
		return 1;
	}

	ret = nfacct_nlmsg_parse_payload(nlh, b);
	CHECK(ret == 0, "nfacct_nlmsg_parse_payload() returned %d", ret);
	CHECK(nfacct_attr_get_str(b, NFACCT_ATTR_NAME) != NULL &&
	      strcmp(nfacct_attr_get_str(b, NFACCT_ATTR_NAME), ACCT_NAME) == 0,
	      "name lost across build_payload/parse_payload");
	CHECK(nfacct_attr_get_u64(b, NFACCT_ATTR_PKTS) == ACCT_PKTS,
	      "pkts lost across build_payload/parse_payload: got %llu",
	      (unsigned long long)nfacct_attr_get_u64(b, NFACCT_ATTR_PKTS));
	CHECK(nfacct_attr_get_u64(b, NFACCT_ATTR_BYTES) == ACCT_BYTES,
	      "bytes lost across build_payload/parse_payload: got %llu",
	      (unsigned long long)nfacct_attr_get_u64(b, NFACCT_ATTR_BYTES));
	CHECK(nfacct_attr_get_u64(b, NFACCT_ATTR_QUOTA) == ACCT_QUOTA,
	      "quota lost across build_payload/parse_payload: got %llu",
	      (unsigned long long)nfacct_attr_get_u64(b, NFACCT_ATTR_QUOTA));
	flags = nfacct_attr_get(b, NFACCT_ATTR_FLAGS);
	CHECK(flags != NULL && *flags == NFACCT_F_QUOTA_PKTS,
	      "flags lost across build_payload/parse_payload");

	/* ---- 5. rendering (use an object with flags == 0: the PLAIN full
	 *         formatter reads the 32-bit flags field through the 64-bit
	 *         accessor, which is an upstream quirk not worth exercising) */
	c = nfacct_alloc();
	CHECK(c != NULL, "third nfacct_alloc() returned NULL");
	if (c == NULL) {
		nfacct_free(b);
		nfacct_free(a);
		return 1;
	}
	nfacct_attr_set_str(c, NFACCT_ATTR_NAME, ACCT_NAME);
	nfacct_attr_set_u64(c, NFACCT_ATTR_PKTS, ACCT_PKTS);
	nfacct_attr_set_u64(c, NFACCT_ATTR_BYTES, ACCT_BYTES);

	memset(buf, 0, sizeof(buf));
	ret = nfacct_snprintf(buf, sizeof(buf), c, NFACCT_SNPRINTF_T_PLAIN,
			      NFACCT_SNPRINTF_F_FULL);
	CHECK(ret > 0, "nfacct_snprintf(PLAIN) returned %d", ret);
	CHECK(strstr(buf, ACCT_NAME) != NULL,
	      "PLAIN output does not contain the name: %s", buf);
	CHECK(strstr(buf, "123456789012345") != NULL,
	      "PLAIN output does not contain the byte counter: %s", buf);

	memset(buf, 0, sizeof(buf));
	ret = nfacct_snprintf(buf, sizeof(buf), c, NFACCT_SNPRINTF_T_JSON,
			      NFACCT_SNPRINTF_F_FULL);
	CHECK(ret > 0, "nfacct_snprintf(JSON) returned %d", ret);
	CHECK(strstr(buf, "\"pkts\"") != NULL,
	      "JSON output does not contain the pkts field: %s", buf);

	nfacct_free(c);
	nfacct_free(b);
	nfacct_free(a);

	if (checks != N_ASSERT) {
		fprintf(stderr, "accounting error: ran %d assertions, expected %d\n",
			checks, N_ASSERT);
		return 1;
	}
	if (fails != 0)
		return 1;

	printf("libnetfilter_acct 1.0.3 consumer test OK: %d/%d assertions "
	       "(attribute round-trip + nfnetlink build/parse round-trip + "
	       "PLAIN/JSON rendering)\n", checks, checks);
	return 0;
}
