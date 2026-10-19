#include <stdio.h>
#include <string.h>

#include <scst_const.h>
#include <scst_user.h>

/* Static contract checks: the SCST version encoding must follow the
 * kernel-style (a<<24)+(b<<16)+(c<<8)+d layout. */
#define STATIC_ASSERT(e) _Static_assert(e, #e)

STATIC_ASSERT(SCST_VERSION(2, 2, 1, 0) == 0x02020100);
STATIC_ASSERT(SCST_VERSION_CODE == SCST_VERSION(2, 2, 1, 0));

/* SCST_USER_PARSE_* interface constants (scst_user.h) must keep the
 * upstream enum ordering — the iscsi-scst / scst_user ABI depends on it. */
STATIC_ASSERT(SCST_USER_PARSE_STANDARD == 0);
STATIC_ASSERT(SCST_USER_PARSE_CALL == 1);
STATIC_ASSERT(SCST_USER_PARSE_EXCEPTION == 2);

int main(void)
{
	int failures = 0;

	/* 1. Version string must carry the exact upstream version. */
	if (strcmp(SCST_VERSION_NAME, "2.2.1") != 0) {
		printf("FAIL: SCST_VERSION_NAME=%s\n", SCST_VERSION_NAME);
		failures++;
	}

	/* 2. Version string must embed the version name. */
	if (strstr(SCST_VERSION_STRING, SCST_VERSION_NAME) == NULL) {
		printf("FAIL: SCST_VERSION_STRING=%s\n", SCST_VERSION_STRING);
		failures++;
	}

	/* 3. Interface revision tag must be a non-empty revision string. */
	if (SCST_CONST_VERSION[0] != '$') {
		printf("FAIL: SCST_CONST_VERSION=%s\n", SCST_CONST_VERSION);
		failures++;
	}

	/* 4. sysfs key mark consumed by iscsi-scst event pump (event.c). */
	if (strcmp(SCST_SYSFS_KEY_MARK, "[key]") != 0) {
		printf("FAIL: SCST_SYSFS_KEY_MARK=%s\n", SCST_SYSFS_KEY_MARK);
		failures++;
	}

	/* 5. scst_user device naming contract. */
	if (strcmp(DEV_USER_NAME, "scst_user") != 0) {
		printf("FAIL: DEV_USER_NAME=%s\n", DEV_USER_NAME);
		failures++;
	}

	if (failures == 0)
		printf("test scst 2.2.1: OK (headers scst_const.h/scst_user.h "
		       "usable from userspace on OHOS)\n");

	return failures == 0 ? 0 : 1;
}
