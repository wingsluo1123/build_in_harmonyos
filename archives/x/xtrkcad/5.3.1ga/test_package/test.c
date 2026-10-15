/*
 * Consumer test for the packaged XTrackCAD libraries.
 *
 * The package is an application, but it ships the static helper libraries the
 * application is built from.  This test links one of them (dynstring, the self
 * contained string helper) through the package's own CMake package files and
 * uses its API the way the rest of the program does.
 */
#include <dynstring.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;

static void check(int ok, const char *what)
{
	if (!ok) {
		fprintf(stderr, "FAIL: %s\n", what);
		failures++;
	}
}

int main(void)
{
	DynString text;

	DynStringMalloc(&text, 0);
	check(DynStringSize(&text) == 0, "new string is empty");

	/* build "XTrkCAD OpenHarmony" through the incremental append API */
	DynStringCatCStr(&text, "XTrkCAD");
	check(DynStringSize(&text) == strlen("XTrkCAD"), "size after first append");
	DynStringCatCStr(&text, " ");
	DynStringCatCStr(&text, "OpenHarmony");
	check(DynStringSize(&text) == strlen("XTrkCAD OpenHarmony"), "size after appends");
	check(strcmp(DynStringToCStr(&text), "XTrkCAD OpenHarmony") == 0, "content after appends");

	/* a copy has to carry the same bytes */
	DynString copy = NaS;
	DynStringDupStr(&copy, &text);
	check(strcmp(DynStringToCStr(&copy), DynStringToCStr(&text)) == 0, "copy content");
	check(DynStringSize(&copy) == DynStringSize(&text), "copy size");

	/* the truncating append stops at the given length */
	DynStringNCatCStr(&copy, 3, " extended");
	check(strcmp(DynStringToCStr(&copy), "XTrkCAD OpenHarmony ex") == 0, "truncating append");
	DynStringFree(&copy);

	DynStringClear(&text);
	check(DynStringSize(&text) == 0, "clear");
	DynStringFree(&text);

	if (failures != 0) {
		fprintf(stderr, "test_xtrkcad: %d check(s) failed\n", failures);
		return 1;
	}
	printf("test_xtrkcad: packaged dynstring library usable, all checks passed\n");
	return 0;
}
