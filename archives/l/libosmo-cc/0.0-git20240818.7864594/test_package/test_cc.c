/* Consumer-side check for libosmo-cc: uses only the installed public headers
 * and the installed shared library. */
#include <stdio.h>
#include <string.h>

#include <osmocom/cc/message.h>

static int failures;

static void check(int cond, const char *what)
{
	if (cond) {
		printf("[ok]   %s\n", what);
	} else {
		printf("[FAIL] %s\n", what);
		failures++;
	}
}

int main(void)
{
	int i;
	const char *name;
	int back;

	check(strcmp(OSMO_CC_VERSION, "OSMOCCv1") == 0,
	      "public header OSMO_CC_VERSION is OSMOCCv1");

	/* Real table lookups implemented in src/message.c. */
	name = osmo_cc_msg_value2name(OSMO_CC_MSG_SETUP_REQ);
	check(name != NULL, "osmo_cc_msg_value2name(SETUP_REQ) returns a name");

	/* Round-trip a handful of IE codes through the exported mapping helpers. */
	{
		static const int ies[] = {
			OSMO_CC_IE_CALLED, OSMO_CC_IE_CALLING, OSMO_CC_IE_PROGRESS,
			OSMO_CC_IE_DISPLAY, OSMO_CC_IE_METERING, OSMO_CC_IE_CAUSE,
			OSMO_CC_IE_BEARER, OSMO_CC_IE_SDP,
		};
		for (i = 0; i < (int)(sizeof(ies) / sizeof(ies[0])); i++) {
			int ie = ies[i];
		name = osmo_cc_ie_value2name(ie);
		back = name ? osmo_cc_ie_name2value(name) : -1;
		if (!name || back != ie) {
			printf("[FAIL] IE round-trip for value %d (name=%s back=%d)\n",
			       ie, name ? name : "(null)", back);
			failures++;
		}
		}
	}
	check(failures == 0, "IE value/name round-trip");

	printf("LIBOSMO_CC_CONSUMER_CHECKS=%d FAILURES=%d\n", 3, failures);
	if (failures) {
		printf("RESULT: FAILED\n");
		return 1;
	}
	printf("LIBOSMO_CC_CONSUMER_OK\n");
	return 0;
}
