#include <stdio.h>
#include <string.h>
#include <pipewire/pipewire.h>

int main(void) {
	const char *version;
	int failed = 0;

	pw_init(NULL, NULL);
	version = pw_get_library_version();
	if (version == NULL || strcmp(version, "1.6.9") != 0) {
		fprintf(stderr, "unexpected library version: %s\n", version ? version : "(null)");
		printf("TEST FAIL: library_version\n");
		failed++;
	} else {
		printf("TEST PASS: library_version (%s)\n", version);
	}
	pw_deinit();
	printf("TEST SUMMARY: %d passed, %d failed\n", failed == 0 ? 1 : 0, failed);
	return failed == 0 ? 0 : 2;
}
